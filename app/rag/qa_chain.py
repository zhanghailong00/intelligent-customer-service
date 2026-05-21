"""
RAG 问答链模块
整合检索和 LLM 生成，实现基于知识库的问答
"""
from typing import Dict, Optional
from app.llm.models import chat
from app.rag.retriever import retrieve
from app.config import RETRIEVAL_TOP_K

# 系统提示词：定义客服角色和回答规范
SYSTEM_PROMPT = """你是实训设备智能客服助手，专门帮助用户解决实训环境搭建、设备使用、故障排查等问题。

回答要求：
1. 基于提供的参考资料回答，确保信息准确
2. 如果资料中有明确答案，直接给出操作步骤或解决方案
3. 如果资料信息不足，诚实告知并建议用户联系人工客服
4. 不要编造或猜测不确定的信息
5. 回答要简洁明了，适合技术人员阅读

回答格式：
- 直接回答问题，不要重复问题
- 如有操作步骤，使用编号列表
- 如有注意事项，用【注意】标注
"""


def build_context(query: str, top_k: int = RETRIEVAL_TOP_K) -> str:
    """
    根据用户问题检索相关文档并构建上下文

    Args:
        query: 用户问题
        top_k: 检索返回的文档数量

    Returns:
        格式化的上下文字符串
    """
    results = retrieve(query, top_k=top_k, include_scores=True)

    if not results:
        return ""

    # 构建上下文，包含文档内容和来源
    context_parts = []
    for i, result in enumerate(results, 1):
        metadata = result["metadata"]
        source = metadata.get("source", "未知来源")
        chapter = metadata.get("chapter", "未知章节")
        score = result.get("score", 0)

        context_parts.append(
            f"【参考资料 {i}】（来源：{source}，章节：{chapter}，相关度：{score}）\n"
            f"{result['content']}"
        )

    return "\n\n".join(context_parts)


def get_references(query: str, top_k: int = RETRIEVAL_TOP_K) -> list:
    """
    获取参考来源列表

    Args:
        query: 用户问题
        top_k: 检索返回的文档数量

    Returns:
        参考来源列表，每个元素包含 source、chapter、score
    """
    results = retrieve(query, top_k=top_k, include_scores=True)

    references = []
    for result in results:
        metadata = result["metadata"]
        references.append({
            "source": metadata.get("source", "未知来源"),
            "chapter": metadata.get("chapter", "未知章节"),
            "score": result.get("score", 0)
        })

    return references


def answer(
    query: str,
    top_k: int = RETRIEVAL_TOP_K,
    temperature: float = 0.3
) -> Dict:
    """
    RAG 问答：检索相关文档并调用 LLM 生成回答

    Args:
        query: 用户问题
        top_k: 检索返回的文档数量
        temperature: LLM 生成温度（越低越确定）

    Returns:
        包含以下字段的字典：
        - answer: 生成的回答
        - references: 参考来源列表
        - has_context: 是否找到相关资料
    """
    # 1. 构建上下文
    context = build_context(query, top_k)

    # 2. 获取参考来源
    references = get_references(query, top_k)

    # 3. 判断是否找到相关资料
    has_context = bool(context)

    # 4. 构建用户消息（包含上下文和问题）
    if has_context:
        user_message = f"""参考资料：
{context}

用户问题：{query}

请基于以上参考资料回答用户问题。如果参考资料中没有相关信息，请说明。"""
    else:
        user_message = f"""用户问题：{query}

知识库中未找到相关资料。请告知用户当前问题可能不在知识库覆盖范围内，建议联系人工客服。"""

    # 5. 调用 LLM 生成回答
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]

    response = chat(messages, temperature=temperature)

    return {
        "answer": response,
        "references": references,
        "has_context": has_context
    }


def format_answer_with_references(result: Dict) -> str:
    """
    将问答结果格式化为带参考来源的完整回答

    Args:
        result: answer() 函数返回的结果

    Returns:
        格式化后的回答字符串
    """
    answer_text = result["answer"]
    references = result["references"]
    has_context = result["has_context"]

    # 基础回答
    output = answer_text

    # 添加参考来源
    if references:
        output += "\n\n---\n**参考来源：**\n"
        for i, ref in enumerate(references, 1):
            output += f"{i}. {ref['source']} - {ref['chapter']}（相关度：{ref['score']}）\n"

    # 如果没有找到相关资料，添加提示
    if not has_context:
        output += "\n\n【提示】当前问题可能不在知识库覆盖范围内，建议联系人工客服获取更准确的帮助。"

    return output
