"""
Query Rewriting 模块（查询改写）

功能：
- 在 RAG 检索前改写用户问题
- 基于历史对话上下文，理解多轮对话中的代词和指代
- 补充缺失上下文、消除模糊指代、扩展关键词
- 提升向量检索的召回率和准确率

技术路线：
- LLM 改写：用 DeepSeek 分析问题并重写
- 历史感知：传入最近 3 轮对话历史，让 LLM 理解上下文
- 降级机制：改写失败时返回原始 query

使用位置：
- Agent.run() 中，retrieve() 之前调用
- 只用于检索，不影响意图分类和 HITL 检测
"""
from typing import List, Optional
from app.llm.models import chat


# 改写 Prompt（带历史上下文）
REWRITE_PROMPT = """你是一个查询优化专家。请将用户问题改写为更适合知识库检索的形式。

当前场景：{context}

对话历史：
{history}

改写要求：
1. 参考对话历史，理解当前问题的上下文
2. 如果当前问题包含代词（"它"、"这个"、"那个"）或省略了主语，根据历史补充完整
3. 补充缺失的上下文（设备名称、场景等）
4. 扩展关键词，让问题更具体
5. 保持原意，不要改变问题方向
6. 如果当前问题已经完整，只需优化表述即可
7. 输出改写后的问题，不要解释

示例：
历史：用户问"传感器不亮了"
当前："怎么修" → "传感器不亮了怎么维修"

历史：用户问"温湿度传感器参数是多少"
当前："光照的呢" → "光照传感器的参数是多少"

用户问题：{query}
改写后："""


def _format_history(messages: list, max_turns: int = 3) -> str:
    """
    将对话历史格式化为改写 prompt 使用的文本

    只取最近 N 轮对话（每轮 = 1条用户消息 + 1条助手回复）。

    Args:
        messages: 对话历史列表（LangChain 消息对象或字典格式）
        max_turns: 最大轮次，默认 3 轮

    Returns:
        格式化的对话文本，如"用户：xxx\n客服：xxx"
    """
    if not messages:
        return "无对话历史"

    # 提取用户和助手的消息
    history_lines = []
    for msg in reversed(messages):
        role = ""
        content = ""

        # LangChain 消息对象
        if hasattr(msg, "type"):
            if msg.type == "human":
                role = "用户"
                content = msg.content
            elif msg.type == "ai":
                role = "客服"
                content = msg.content
        # 字典格式
        elif isinstance(msg, dict):
            role_map = {"user": "用户", "assistant": "客服"}
            role = role_map.get(msg.get("role", ""), "")
            content = msg.get("content", "")

        # 处理 content 是列表格式的情况（LangChain v0.2+）
        # 格式如：[{"type": "text", "text": "..."}]
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            content = " ".join(text_parts)

        if role and content:
            # 截断过长的内容
            if len(content) > 100:
                content = content[:100] + "..."
            history_lines.insert(0, f"{role}：{content}")

        # 收集够 max_turns * 2 条消息（用户+客服各算一条）
        if len(history_lines) >= max_turns * 2:
            break

    return "\n".join(history_lines) if history_lines else "无对话历史"


def rewrite_query(
    query: str,
    context: str = "",
    history: Optional[list] = None
) -> str:
    """
    查询改写（基于历史对话上下文）

    将用户问题改写为更适合向量检索的形式。
    如果提供了对话历史，LLM 会参考历史理解当前问题的上下文。

    Args:
        query: 原始用户问题
        context: 场景上下文（如"产品专家"、"故障排查"、"培训指导"）
        history: 对话历史列表（可选），支持 LangChain 消息对象和字典格式

    Returns:
        改写后的问题，改写失败时返回原始 query
    """
    # 空 query 直接返回
    if not query or not query.strip():
        return query

    print(f"[Rewriter] 原始 query：{query}")

    # 格式化历史对话
    history_text = _format_history(history)
    print(f"[Rewriter] 参考历史：{history_text[:80]}...")

    try:
        # 调用 LLM 改写（传入历史上下文）
        response = chat(
            messages=[
                {"role": "system", "content": REWRITE_PROMPT.format(
                    context=context or "通用客服场景",
                    history=history_text,
                    query=query
                )}
            ],
            temperature=0.3  # 低温度，确保输出稳定
        )

        rewritten = response.strip()

        # 验证：改写结果不能为空
        if rewritten and len(rewritten) > 0:
            print(f"[Rewriter] 改写后：{rewritten}")
            return rewritten
        else:
            print(f"[Rewriter] 改写结果为空，使用原始 query")
            return query

    except Exception as e:
        print(f"[Rewriter] 改写失败：{e}，使用原始 query")
        return query
