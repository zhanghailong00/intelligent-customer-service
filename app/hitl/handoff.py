"""
HITL 会话快照模块（Session Handoff）

功能：
- 在转人工时生成会话快照
- 提取核心诉求、生成建议方案
- 传递给人工客服，实现无缝接力

快照字段：
- core_need: 用户核心诉求（一句话总结）
- hitl_reason: 转人工原因（已有）
- suggested_plan: 建议处理方案（LLM 生成）
- history: 完整对话历史（已有）
"""
from app.llm.models import chat


# 快照生成的 System Prompt
HANDOFF_SYSTEM_PROMPT = """你是一个智能客服系统的会话分析师。
当 AI 客服无法处理用户问题需要转接人工时，你需要分析对话并生成会话快照。

请根据以下信息，输出 JSON 格式的分析结果：
1. core_need：用户的核心诉求（一句话总结，不超过 30 字）
2. suggested_plan：人工客服的处理建议（2-3 条具体步骤）

要求：
- 分析要准确，基于对话实际内容
- 建议要具体可执行，不要空泛
- 使用中文输出
- 只输出 JSON，不要输出其他内容

输出格式：
{"core_need": "...", "suggested_plan": "1. ...\n2. ...\n3. ..."}"""


def generate_snapshot(
    messages: list,
    answer: str,
    sources: list,
    hitl_reason: str,
    confidence: float = 1.0
) -> dict:
    """
    生成会话快照

    调用 LLM 分析对话历史，提取核心诉求并生成建议方案。

    Args:
        messages: 对话历史（LangChain 消息对象或字典格式）
        answer: Agent 生成的回答
        sources: 参考来源
        hitl_reason: 转人工原因
        confidence: 意图分类置信度

    Returns:
        {
            "core_need": "用户核心诉求",
            "hitl_reason": "转人工原因",
            "suggested_plan": "建议处理方案",
            "history": "格式化的对话历史"
        }
    """
    # 1. 格式化对话历史
    history_text = _format_history(messages)

    # 2. 构建 LLM 输入
    user_prompt = f"""对话历史：
{history_text}

Agent 回答：{answer}

参考来源：{', '.join(sources) if sources else '无'}

转人工原因：{hitl_reason}

意图置信度：{confidence:.0%}

请分析用户核心诉求并给出处理建议。"""

    # 3. 调用 LLM 生成分析结果
    try:
        response = chat(
            messages=[
                {"role": "system", "content": HANDOFF_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3  # 低温度，确保输出稳定
        )

        # 4. 解析 LLM 输出
        snapshot = _parse_snapshot(response)
        snapshot["hitl_reason"] = hitl_reason
        snapshot["history"] = history_text

        print(f"[HITL] 会话快照生成成功")
        return snapshot

    except Exception as e:
        print(f"[HITL] 会话快照生成失败：{e}")
        # 降级：返回基础快照（不调用 LLM）
        return {
            "core_need": "（快照生成失败，请查看对话历史）",
            "hitl_reason": hitl_reason,
            "suggested_plan": "请查看对话历史了解用户问题",
            "history": history_text
        }


def _format_history(messages: list) -> str:
    """
    将对话历史格式化为可读文本

    兼容 LangChain 消息对象和字典格式。

    Args:
        messages: 对话历史列表

    Returns:
        格式化的对话文本
    """
    lines = []
    for msg in messages:
        role = ""
        content = ""

        # LangChain 消息对象
        if hasattr(msg, "type") and msg.type == "human":
            role = "用户"
            content = msg.content
        elif hasattr(msg, "type") and msg.type == "ai":
            role = "AI客服"
            content = msg.content
        elif hasattr(msg, "type") and msg.type == "system":
            role = "系统"
            content = msg.content
        # 字典格式
        elif isinstance(msg, dict):
            role_map = {"user": "用户", "assistant": "AI客服", "system": "系统"}
            role = role_map.get(msg.get("role", ""), msg.get("role", ""))
            content = msg.get("content", "")

        if role and content:
            lines.append(f"{role}：{content}")

    return "\n".join(lines) if lines else "无对话历史"


def _parse_snapshot(llm_output: str) -> dict:
    """
    解析 LLM 输出的 JSON 快照

    Args:
        llm_output: LLM 生成的文本

    Returns:
        解析后的快照字典
    """
    import json

    # 尝试提取 JSON 部分
    text = llm_output.strip()

    # 如果包含 markdown 代码块，提取其中的 JSON
    if "```" in text:
        import re
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            text = json_match.group(1).strip()

    try:
        data = json.loads(text)
        return {
            "core_need": data.get("core_need", "未提取到"),
            "suggested_plan": data.get("suggested_plan", "暂无建议")
        }
    except json.JSONDecodeError:
        # JSON 解析失败，尝试提取关键信息
        print(f"[HITL] JSON 解析失败，原始输出：{text[:200]}")
        return {
            "core_need": text[:100] if text else "未提取到",
            "suggested_plan": "请查看对话历史"
        }


def format_snapshot_display(snapshot: dict) -> str:
    """
    将会话快照格式化为 Gradio 显示文本

    Args:
        snapshot: 会话快照字典

    Returns:
        格式化的显示文本
    """
    lines = []
    lines.append("──────────────────────")
    lines.append("  会话快照")
    lines.append("──────────────────────")
    lines.append(f"核心诉求：{snapshot.get('core_need', '未提取')}")
    lines.append(f"转人工原因：{snapshot.get('hitl_reason', '未知')}")

    plan = snapshot.get("suggested_plan", "暂无建议")
    lines.append("建议方案：")
    for line in plan.split("\n"):
        if line.strip():
            lines.append(f"  {line.strip()}")

    lines.append("──────────────────────")

    return "\n".join(lines)
