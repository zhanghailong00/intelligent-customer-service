"""
Agent 基类

所有 Agent 的父类，定义统一的接口和公共逻辑：
- 每个 Agent 有独立的 System Prompt（角色定位不同）
- 共享同一个 RAG 检索（同一个 ChromaDB）
- 调用同一个 LLM 生成回答（支持 Fallback）
"""
from typing import Dict, List, Optional
from app.llm.models import chat
from app.rag.retriever import retrieve, retrieve_with_context


class BaseAgent:
    """
    Agent 基类

    子类只需覆写 system_prompt 属性，其他逻辑复用。
    """

    # 子类必须覆写
    name: str = "base"
    role_name: str = "助手"  # 用于 UI 显示的角色名称
    system_prompt: str = "你是一个智能客服助手。"

    def __init__(self):
        """初始化 Agent"""
        pass

    def run(self, user_query: str, top_k: int = 3) -> Dict[str, any]:
        """
        执行 Agent 逻辑：检索 + 生成

        Args:
            user_query: 用户的问题
            top_k: 检索返回的文档数量

        Returns:
            回答字典：
            - answer: LLM 生成的回答
            - sources: 参考来源列表
            - intent: Agent 的意图类型
        """
        # 1. 从知识库检索相关内容
        retrieval_results = retrieve(user_query, top_k=top_k, include_scores=False)

        # 2. 构建上下文
        context = self._build_context(retrieval_results)

        # 3. 构建消息列表
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"参考资料：\n{context}\n\n用户问题：{user_query}"}
        ]

        # 4. 调用 LLM 生成回答
        answer = chat(messages)

        # 5. 提取参考来源
        sources = [r["metadata"].get("source", "") for r in retrieval_results]

        return {
            "answer": answer,
            "sources": sources,
            "intent": self.name
        }

    def _build_context(self, results: List[Dict]) -> str:
        """
        将检索结果构建为上下文字符串

        Args:
            results: 检索结果列表

        Returns:
            格式化的上下文字符串
        """
        if not results:
            return "未找到相关文档内容。"

        context_parts = []
        for i, result in enumerate(results, 1):
            metadata = result["metadata"]
            source = metadata.get("source", "未知来源")
            chapter = metadata.get("chapter", "未知章节")
            context_parts.append(
                f"【文档 {i}】来源：{source} | 章节：{chapter}\n{result['content']}"
            )

        return "\n\n".join(context_parts)
