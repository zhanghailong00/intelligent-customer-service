"""
Agent 基类

所有 Agent 的父类，定义统一的接口和公共逻辑：
- 每个 Agent 有独立的 System Prompt（角色定位不同）
- 共享同一个 RAG 检索（同一个 ChromaDB）
- 调用同一个 LLM 生成回答（支持 Fallback）
- 支持对话历史（messages），实现多轮对话记忆
- 支持查询改写（Query Rewriting），提升检索质量
- 两步检索：原始 query + 改写后 query，合并去重
"""
from typing import Dict, List, Optional
from app.llm.models import chat
from app.rag.retriever import retrieve, retrieve_with_context
from app.query.rewriter import rewrite_query

# 对话历史保留的最大条数（避免 token 溢出）
MAX_HISTORY_LENGTH = 10


class BaseAgent:
    """
    Agent 基类

    子类只需覆写 system_prompt 和 role_name 属性，其他逻辑复用。
    """

    # 子类必须覆写
    name: str = "base"
    role_name: str = "助手"  # 用于 UI 显示的角色名称
    system_prompt: str = "你是一个智能客服助手。"

    def __init__(self):
        """初始化 Agent"""
        pass

    def run(self, user_query: str, messages: list = None, top_k: int = 3) -> Dict[str, any]:
        """
        执行 Agent 逻辑：查询改写 + 两步检索 + 生成

        流程：
        1. 查询改写：基于历史对话，将用户问题改写为更适合检索的形式
        2. 两步检索：用原始 query 和改写后 query 分别检索，合并去重
        3. 构建上下文：格式化检索结果
        4. LLM 生成：用原始 query + 上下文生成回答

        Args:
            user_query: 用户的问题（原始 query）
            messages: 对话历史（LangGraph State 中的 messages 列表）
            top_k: 检索返回的文档数量

        Returns:
            回答字典：
            - answer: LLM 生成的回答
            - sources: 参考来源列表
            - intent: Agent 的意图类型
        """
        # 1. 查询改写（基于历史对话上下文）
        rewritten_query = rewrite_query(user_query, self.role_name, messages)

        # 2. 两步检索：原始 query + 改写后 query，合并去重
        retrieval_results = self._two_step_retrieve(user_query, rewritten_query, top_k)

        # 3. 构建上下文
        context = self._build_context(retrieval_results)

        # 4. 构建消息列表（用原始 query，保持用户视角）
        llm_messages = self._build_messages(user_query, context, messages)

        # 5. 调用 LLM 生成回答
        answer = chat(llm_messages)

        # 6. 提取参考来源
        sources = [r["metadata"].get("source", "") for r in retrieval_results]

        return {
            "answer": answer,
            "sources": sources,
            "intent": self.name
        }

    def _two_step_retrieve(self, original_query: str, rewritten_query: str, top_k: int) -> List[Dict]:
        """
        两步检索：原始 query + 改写后 query，合并去重

        流程：
        1. 用原始 query 检索
        2. 用改写后 query 检索
        3. 合并两组结果，按 source 去重，返回 top_k 条

        Args:
            original_query: 原始用户问题
            rewritten_query: 改写后的问题
            top_k: 最终返回的文档数量

        Returns:
            合并去重后的检索结果列表
        """
        print(f"[Agent] 两步检索开始")
        print(f"[Agent] 原始 query：{original_query}")
        print(f"[Agent] 改写后 query：{rewritten_query}")

        # Step 1: 用原始 query 检索
        results_original = retrieve(original_query, top_k=top_k, include_scores=True)
        print(f"[Agent] 原始 query 检索到 {len(results_original)} 条结果")

        # Step 2: 用改写后 query 检索
        results_rewritten = retrieve(rewritten_query, top_k=top_k, include_scores=True)
        print(f"[Agent] 改写后 query 检索到 {len(results_rewritten)} 条结果")

        # Step 3: 合并去重（按 source 字段去重，保留分数高的）
        # 过滤掉 metadata 为 None 的结果（向量数据库可能为空或数据异常）
        merged = {}
        for r in results_original + results_rewritten:
            # 安全检查：metadata 可能为 None
            metadata = r.get("metadata")
            if metadata is None:
                print(f"[Agent] 警告：跳过 metadata 为空的结果")
                continue
            source = metadata.get("source", "")
            score = r.get("score", 0)
            # 如果 source 已存在，保留分数高的
            if source not in merged or score > merged[source].get("score", 0):
                merged[source] = r

        # 按分数排序，取 top_k
        merged_list = sorted(merged.values(), key=lambda x: x.get("score", 0), reverse=True)
        final_results = merged_list[:top_k]

        print(f"[Agent] 合并去重后：{len(merged)} 条，取 top {top_k}：{len(final_results)} 条")

        # 移除 score 字段（后续不需要）
        for r in final_results:
            r.pop("score", None)

        return final_results

    def _build_messages(self, user_query: str, context: str, messages: list = None) -> list:
        """
        构建 LLM 消息列表，包含对话历史

        Args:
            user_query: 当前用户问题
            context: 检索到的参考资料上下文
            messages: 对话历史（可选）

        Returns:
            消息列表，格式：[system, history..., user_with_context]
        """
        # 基础消息：system prompt
        llm_messages = [
            {"role": "system", "content": self.system_prompt}
        ]

        # 添加对话历史（截取最近 N 条，避免 token 溢出）
        if messages:
            # 过滤掉 system 消息，只保留 user 和 assistant
            # 兼容 LangChain 消息对象和字典格式
            history = []
            for m in messages:
                # LangChain 消息对象
                if hasattr(m, "type"):
                    if m.type in ("human", "ai"):
                        history.append({"role": "user" if m.type == "human" else "assistant", "content": m.content})
                # 字典格式
                elif isinstance(m, dict) and m.get("role") in ("user", "assistant"):
                    history.append(m)
            # 截取最近的消息
            recent_history = history[-MAX_HISTORY_LENGTH:] if len(history) > MAX_HISTORY_LENGTH else history
            llm_messages.extend(recent_history)

        # 添加当前问题（带上参考资料）
        llm_messages.append({
            "role": "user",
            "content": f"参考资料：\n{context}\n\n用户问题：{user_query}"
        })

        return llm_messages

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
