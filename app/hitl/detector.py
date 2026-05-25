"""
HITL（Human-in-the-Loop）检测模块

功能：
- 检测是否需要人工介入
- 三种必做检测：Agent 拒绝、用户主动要求、置信度低
- 两种可选检测：敏感问题、情绪波动（后续扩展）

设计思路：
- 检测逻辑独立成模块，便于维护和扩展
- 每个检测函数返回 bool，hitl_checker 综合判断
- 关键词匹配为主，简单高效，零成本
"""
from typing import List


# ==================== 关键词库 ====================

# Agent 拒绝关键词：当回复包含这些词时，认为 Agent 无法回答
REFUSAL_KEYWORDS = [
    "我不确定",
    "无法确定",
    "建议联系技术支持",
    "建议联系售后",
    "没有找到相关",
    "目前没有相关信息",
    "无法回答",
    "抱歉，我无法",
    "超出了我的能力范围",
]

# 用户主动要求转人工关键词
HUMAN_REQUEST_KEYWORDS = [
    "转人工",
    "找客服",
    "人工客服",
    "人工服务",
    "转接人工",
    "找人工",
    "真人客服",
    "真人服务",
]

# 敏感问题关键词：涉及退款、投诉、法律等（可选检测）
SENSITIVE_KEYWORDS = [
    "退款",
    "投诉",
    "法律",
    "赔偿",
    "找领导",
    "工商",
    "消费者权益",
    "三包",
    "退货",
]


# ==================== 检测函数 ====================

def check_agent_refusal(answer: str) -> bool:
    """
    检测 Agent 回复是否包含拒绝表述

    Args:
        answer: Agent 生成的回答

    Returns:
        True 表示 Agent 无法回答，需要人工介入
    """
    for keyword in REFUSAL_KEYWORDS:
        if keyword in answer:
            print(f"[HITL] 检测到 Agent 拒绝关键词：{keyword}")
            return True
    return False


def check_user_request_human(messages: List[dict]) -> bool:
    """
    检测用户是否主动要求转人工

    从对话历史中查找用户消息，检查是否包含转人工关键词。

    Args:
        messages: 对话历史

    Returns:
        True 表示用户主动要求转人工
    """
    # 只检查最近的用户消息（避免历史消息干扰）
    recent_user_messages = []
    for msg in reversed(messages):
        # 兼容 LangChain 消息对象和字典格式
        content = ""
        if hasattr(msg, "type") and msg.type == "human":
            content = msg.content
        elif isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content", "")

        if content:
            recent_user_messages.append(content)
            if len(recent_user_messages) >= 3:  # 只检查最近 3 条
                break

    # 检查是否包含转人工关键词
    for msg in recent_user_messages:
        for keyword in HUMAN_REQUEST_KEYWORDS:
            if keyword in msg:
                print(f"[HITL] 检测到用户主动要求转人工：{keyword}")
                return True
    return False


def check_low_confidence(confidence: float, threshold: float = 0.5) -> bool:
    """
    检测置信度是否低于阈值

    Args:
        confidence: 意图分类置信度
        threshold: 置信度阈值，默认 0.5

    Returns:
        True 表示置信度低，需要人工介入
    """
    if confidence < threshold:
        print(f"[HITL] 置信度 {confidence:.2f} 低于阈值 {threshold}")
        return True
    return False


def check_sensitive_content(query: str) -> bool:
    """
    检测是否包含敏感内容（可选检测）

    Args:
        query: 用户的问题

    Returns:
        True 表示包含敏感内容，需要人工介入
    """
    for keyword in SENSITIVE_KEYWORDS:
        if keyword in query:
            print(f"[HITL] 检测到敏感关键词：{keyword}")
            return True
    return False


# ==================== 综合判断 ====================

def should_escalate_to_human(
    answer: str,
    messages: List[dict],
    confidence: float,
    user_query: str = ""
) -> dict:
    """
    综合判断是否需要转人工

    检查三个必做条件：
    1. Agent 拒绝（回复包含拒绝关键词）
    2. 用户主动要求（用户说"转人工"）
    3. 置信度低（confidence < 0.5）

    可选条件（后续扩展）：
    4. 敏感问题
    5. 情绪波动

    Args:
        answer: Agent 生成的回答
        messages: 对话历史
        confidence: 意图分类置信度
        user_query: 用户的原始问题（用于敏感内容检测）

    Returns:
        {
            "needs_human": True/False,
            "reason": "拒绝回答"/"用户要求"/"置信度低"/"无"
        }
    """
    # 必做检测 1：Agent 拒绝
    if check_agent_refusal(answer):
        return {"needs_human": True, "reason": "拒绝回答"}

    # 必做检测 2：用户主动要求
    if check_user_request_human(messages):
        return {"needs_human": True, "reason": "用户要求"}

    # 必做检测 3：置信度低
    if check_low_confidence(confidence):
        return {"needs_human": True, "reason": "置信度低"}

    # 可选检测：敏感问题（后续启用）
    # if check_sensitive_content(user_query):
    #     return {"needs_human": True, "reason": "敏感问题"}

    return {"needs_human": False, "reason": "无"}
