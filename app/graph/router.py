"""
路由器模块

功能：
- 根据意图分类结果，分发到对应的 Agent
- 处理未知意图的兜底逻辑
- 返回完整的回答结果（答案 + 来源 + 意图信息）

设计思路：
- 当前用 if-else 路由（简单可控）
- Phase 5 需要人工审核时，再引入 LangGraph
- unknown 意图不走 Agent，直接返回通用回复（避免无关检索结果）
"""
from typing import Dict
from app.llm.intent_classifier import (
    classify_intent,
    get_intent_label,
    INTENT_PRODUCT,
    INTENT_FAULT,
    INTENT_TRAINING,
    INTENT_GREETING,
    INTENT_UNKNOWN
)
from app.agents.product import ProductAgent
from app.agents.fault import FaultAgent
from app.agents.training import TrainingAgent

# 初始化 Agent 实例（全局单例，避免重复创建）
_agents = {
    INTENT_PRODUCT: ProductAgent(),
    INTENT_FAULT: FaultAgent(),
    INTENT_TRAINING: TrainingAgent(),
}

# 打招呼的友好回复（不检索知识库，引导用户提问）
GREETING_RESPONSE = "你好！我是智科云联的实训设备智能客服，可以帮你解答以下问题：\n\n- **产品咨询**：设备功能、参数、使用方法\n- **故障排查**：设备故障、报错、异常处理\n- **培训指导**：实验指导、教学资料、课件\n\n请问有什么可以帮您的？"

# 未知意图的通用回复（不检索知识库，不给参考来源）
UNKNOWN_RESPONSE = "抱歉，您的问题似乎与实训设备无关。我主要负责回答关于实训设备的产品咨询、故障排查和培训指导问题。请问有什么关于实训设备的问题我可以帮您？"


def route(user_query: str) -> Dict[str, any]:
    """
    路由入口：意图分类 → 选择 Agent → 执行

    Args:
        user_query: 用户的问题

    Returns:
        回答字典：
        - answer: LLM 生成的回答
        - sources: 参考来源列表
        - intent: 意图类型
        - intent_label: 意图中文标签
        - confidence: 意图分类置信度
    """
    # 1. 意图分类
    intent_result = classify_intent(user_query)
    intent = intent_result["intent"]
    confidence = intent_result["confidence"]

    print(f"[路由] 意图：{get_intent_label(intent)} ({intent})，置信度：{confidence:.2f}")

    # 2. 打招呼直接返回友好回复（不走 Agent，不检索知识库）
    if intent == INTENT_GREETING:
        print(f"[路由] 打招呼，返回友好回复")
        return {
            "answer": GREETING_RESPONSE,
            "sources": [],
            "intent": intent,
            "intent_label": get_intent_label(intent),
            "confidence": confidence
        }

    # 3. 未知意图直接返回通用回复（不走 Agent，不检索知识库）
    if intent == INTENT_UNKNOWN:
        print(f"[路由] 未知意图，直接返回通用回复")
        return {
            "answer": UNKNOWN_RESPONSE,
            "sources": [],
            "intent": intent,
            "intent_label": get_intent_label(intent),
            "confidence": confidence
        }

    # 4. 选择 Agent 并执行
    agent = _agents[intent]
    result = agent.run(user_query)

    # 5. 补充意图信息
    result["intent"] = intent
    result["intent_label"] = get_intent_label(intent)
    result["confidence"] = confidence

    return result
