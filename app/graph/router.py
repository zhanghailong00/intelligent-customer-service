"""
路由器模块

功能：
- 根据意图分类结果，分发到对应的 Agent
- 处理未知意图的兜底逻辑
- 返回完整的回答结果（答案 + 来源 + 意图信息）

设计思路：
- 当前用 if-else 路由（简单可控）
- Phase 5 需要人工审核时，再引入 LangGraph
"""
from typing import Dict
from app.llm.intent_classifier import (
    classify_intent,
    get_intent_label,
    INTENT_PRODUCT,
    INTENT_FAULT,
    INTENT_TRAINING,
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

    # 2. 选择 Agent 并执行
    if intent in _agents:
        agent = _agents[intent]
        result = agent.run(user_query)
    else:
        # 兜底：使用产品 Agent（最通用）
        print(f"[路由] 未知意图，使用产品 Agent 兜底")
        agent = _agents[INTENT_PRODUCT]
        result = agent.run(user_query)

    # 3. 补充意图信息
    result["intent"] = intent
    result["intent_label"] = get_intent_label(intent)
    result["confidence"] = confidence

    return result
