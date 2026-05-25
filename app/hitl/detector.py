"""
HITL（Human-in-the-Loop）检测模块

功能：
- 检测是否需要人工介入
- 前置检测：系统控制意图（转人工、投诉等），在路由前拦截
- 后置检测：Agent 失败兜底（拒绝回答、低置信度等）

设计思路：
- 双层 HITL 架构：前置规则检测 + 后置兜底检测
- 前置检测：规则匹配，毫秒级响应，不消耗 LLM token
- 后置检测：Agent 执行完后兜底，处理 RAG 召回低、Agent 拒绝等场景
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

# 敏感问题关键词：涉及退款、投诉、法律等
SENSITIVE_KEYWORDS = [
    "退款",
    "退货",
    "投诉",
    "法律",
    "赔偿",
    "找领导",
    "工商",
    "消费者权益",
    "三包",
]

# ==================== 前置检测：系统控制意图 ====================
# 系统控制意图：优先级最高，在路由前拦截
# 不走 LLM 分类，规则匹配即可（确定性强、速度快、零成本）

# 转人工意图关键词（覆盖常见口语化表达）
HANDOFF_KEYWORDS = [
    "转人工",
    "找客服",
    "人工客服",
    "人工服务",
    "转接人工",
    "找人工",
    "真人客服",
    "真人服务",
    "接人工",
    "帮我转",
    "我要人工",
    "和真人聊",
    "和人聊",
    "不想和机器人",
    "不要机器人",
]

# 投诉/维权意图关键词
COMPLAINT_KEYWORDS = [
    "投诉",
    "我要投诉",
    "找你们领导",
    "找领导",
    "负责人",
    "上级",
    "管理层",
    "消协",
    "工商局",
    "消费者协会",
    "12315",
]

# 售后/退款意图关键词（可能需要人工处理）
AFTERSALE_KEYWORDS = [
    "退款",
    "退货",
    "换货",
    "赔偿",
    "三包",
    "维权",
    "法律",
    "起诉",
    "律师",
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
    检测是否包含敏感内容

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


# ==================== 前置检测函数 ====================

def check_system_control(query: str) -> dict:
    """
    前置检测：系统控制意图（转人工、投诉、售后维权）

    在意图分类之前执行，优先级最高。
    规则匹配，不走 LLM，毫秒级响应。

    Args:
        query: 用户的原始问题

    Returns:
        {
            "is_system_control": True/False,
            "type": "handoff"/"complaint"/"aftersale"/None,
            "message": "给用户的提示信息"
        }
    """
    # 检测转人工意图
    for keyword in HANDOFF_KEYWORDS:
        if keyword in query:
            print(f"[HITL 前置] 检测到转人工意图：{keyword}")
            return {
                "is_system_control": True,
                "type": "handoff",
                "message": "正在为您转接人工客服，请稍候...\n\n请描述您的问题，人工客服将为您处理。"
            }

    # 检测投诉/维权意图
    for keyword in COMPLAINT_KEYWORDS:
        if keyword in query:
            print(f"[HITL 前置] 检测到投诉意图：{keyword}")
            return {
                "is_system_control": True,
                "type": "complaint",
                "message": "收到您的投诉/反馈，已为您转接人工客服。\n\n请描述具体问题，我们将尽快为您处理。"
            }

    # 检测售后/退款意图
    for keyword in AFTERSALE_KEYWORDS:
        if keyword in query:
            print(f"[HITL 前置] 检测到售后意图：{keyword}")
            return {
                "is_system_control": True,
                "type": "aftersale",
                "message": "您的售后问题需要人工客服处理。\n\n已为您转接人工客服，请描述具体问题。"
            }

    return {
        "is_system_control": False,
        "type": None,
        "message": ""
    }


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

    # 必做检测 4：敏感问题
    if check_sensitive_content(user_query):
        return {"needs_human": True, "reason": "敏感问题"}

    return {"needs_human": False, "reason": "无"}
