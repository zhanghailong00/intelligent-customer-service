"""
LangGraph 节点函数

功能：
- 实现状态图中的各个节点逻辑
- 每个节点读取 State、执行逻辑、写入 State
- 节点之间通过 State 传递数据

节点设计：
- classifier_node: 意图分类，决定路由方向
- greeting_node: 返回打招呼的友好回复
- unknown_node: 返回无关问题的通用回复
- product_agent_node: 调用产品知识 Agent
- fault_agent_node: 调用故障排查 Agent
- training_agent_node: 调用培训资料 Agent
"""
from app.graph.state import State
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
_product_agent = ProductAgent()
_fault_agent = FaultAgent()
_training_agent = TrainingAgent()

# Agent 映射表：intent → agent 实例
_agents = {
    INTENT_PRODUCT: _product_agent,
    INTENT_FAULT: _fault_agent,
    INTENT_TRAINING: _training_agent,
}

# 打招呼的友好回复（不检索知识库，引导用户提问）
GREETING_RESPONSE = "你好！我是智科云联的实训设备智能客服，可以帮你解答以下问题：\n\n- **产品咨询**：设备功能、参数、使用方法\n- **故障排查**：设备故障、报错、异常处理\n- **培训指导**：实验指导、教学资料、课件\n\n请问有什么可以帮您的？"

# 未知意图的通用回复（不检索知识库，不给参考来源）
UNKNOWN_RESPONSE = "抱歉，您的问题似乎与实训设备无关。我主要负责回答关于实训设备的产品咨询、故障排查和培训指导问题。请问有什么关于实训设备的问题我可以帮您？"


def classifier_node(state: State) -> dict:
    """
    意图分类节点

    功能：
    - 接收用户最新的消息
    - 调用 LLM 意图分类器
    - 设置 intent、confidence、role_name
    - greeting 和 unknown 意图直接设置 answer（不走 Agent）

    Args:
        state: 当前对话状态

    Returns:
        更新后的状态字段
    """
    # 从 messages 中获取最新的用户消息
    messages = state["messages"]
    # messages 是 [{"role": "user", "content": "..."}, ...] 格式
    # 取最后一条用户消息
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg["content"]
            break

    if not user_message:
        # 没有用户消息，返回未知意图
        return {
            "intent": INTENT_UNKNOWN,
            "confidence": 0.0,
            "role_name": "",
            "answer": UNKNOWN_RESPONSE,
            "sources": [],
            "hitl_required": False
        }

    # 调用意图分类器
    intent_result = classify_intent(user_message)
    intent = intent_result["intent"]
    confidence = intent_result["confidence"]

    print(f"[LangGraph] 意图：{get_intent_label(intent)} ({intent})，置信度：{confidence:.2f}")

    # 基础返回值
    result = {
        "intent": intent,
        "confidence": confidence,
        "role_name": "",
        "answer": "",
        "sources": [],
        "hitl_required": False
    }

    # greeting 和 unknown 直接设置回复，不走 Agent
    if intent == INTENT_GREETING:
        print(f"[LangGraph] 打招呼，返回友好回复")
        result["role_name"] = ""
        result["answer"] = GREETING_RESPONSE
    elif intent == INTENT_UNKNOWN:
        print(f"[LangGraph] 未知意图，返回通用回复")
        result["role_name"] = ""
        result["answer"] = UNKNOWN_RESPONSE
    else:
        # 已知意图，设置 role_name，交给对应的 Agent 节点处理
        agent = _agents.get(intent)
        if agent:
            result["role_name"] = agent.role_name

    return result


def greeting_node(state: State) -> dict:
    """
    打招呼回复节点

    功能：返回打招呼的友好回复（classifier 已设置 answer，此节点确认）

    Args:
        state: 当前对话状态

    Returns:
        更新后的状态字段
    """
    # answer 已在 classifier_node 中设置，这里直接返回
    return {
        "answer": state.get("answer", GREETING_RESPONSE),
        "sources": []
    }


def unknown_node(state: State) -> dict:
    """
    未知意图回复节点

    功能：返回无关问题的通用回复（classifier 已设置 answer，此节点确认）

    Args:
        state: 当前对话状态

    Returns:
        更新后的状态字段
    """
    # answer 已在 classifier_node 中设置，这里直接返回
    return {
        "answer": state.get("answer", UNKNOWN_RESPONSE),
        "sources": []
    }


def product_agent_node(state: State) -> dict:
    """
    产品知识 Agent 节点

    功能：调用产品知识 Agent，检索知识库并生成回答

    Args:
        state: 当前对话状态

    Returns:
        更新后的状态字段
    """
    # 获取最新的用户消息
    user_message = _get_last_user_message(state)
    messages = state.get("messages", [])

    # 调用 Agent
    result = _product_agent.run(user_message, messages=messages)

    return {
        "answer": result["answer"],
        "sources": result["sources"]
    }


def fault_agent_node(state: State) -> dict:
    """
    故障排查 Agent 节点

    功能：调用故障排查 Agent，检索知识库并生成回答

    Args:
        state: 当前对话状态

    Returns:
        更新后的状态字段
    """
    # 获取最新的用户消息
    user_message = _get_last_user_message(state)
    messages = state.get("messages", [])

    # 调用 Agent
    result = _fault_agent.run(user_message, messages=messages)

    return {
        "answer": result["answer"],
        "sources": result["sources"]
    }


def training_agent_node(state: State) -> dict:
    """
    培训资料 Agent 节点

    功能：调用培训资料 Agent，检索知识库并生成回答

    Args:
        state: 当前对话状态

    Returns:
        更新后的状态字段
    """
    # 获取最新的用户消息
    user_message = _get_last_user_message(state)
    messages = state.get("messages", [])

    # 调用 Agent
    result = _training_agent.run(user_message, messages=messages)

    return {
        "answer": result["answer"],
        "sources": result["sources"]
    }


def _get_last_user_message(state: State) -> str:
    """
    从 State 中提取最新的用户消息

    Args:
        state: 当前对话状态

    Returns:
        最新的用户消息文本
    """
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg["content"]
    return ""


def route_by_intent(state: State) -> str:
    """
    条件边函数：根据 intent 决定路由到哪个节点

    Args:
        state: 当前对话状态

    Returns:
        下一个节点的名称
    """
    intent = state.get("intent", INTENT_UNKNOWN)

    # greeting 和 unknown 直接走各自的节点
    if intent == INTENT_GREETING:
        return "greeting_node"
    elif intent == INTENT_UNKNOWN:
        return "unknown_node"
    # 已知意图走对应的 Agent 节点
    elif intent == INTENT_PRODUCT:
        return "product_agent_node"
    elif intent == INTENT_FAULT:
        return "fault_agent_node"
    elif intent == INTENT_TRAINING:
        return "training_agent_node"
    else:
        # 兜底：未知意图
        return "unknown_node"
