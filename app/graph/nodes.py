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
- hitl_checker_node: 检测是否需要人工介入
"""
from app.graph.state import State
from app.hitl.detector import should_escalate_to_human, check_system_control
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
    - 前置检测：系统控制意图（转人工、投诉、售后），优先级最高
    - 调用 LLM 意图分类器（仅在未命中系统控制意图时）
    - 设置 intent、confidence、role_name
    - greeting 和 unknown 意图直接设置 answer（不走 Agent）

    设计：前置规则检测 + 后置兜底检测（双层 HITL）

    Args:
        state: 当前对话状态

    Returns:
        更新后的状态字段
    """
    # 从 messages 中获取最新的用户消息
    messages = state["messages"]
    # 兼容 LangChain HumanMessage 对象和字典格式
    user_message = ""
    for msg in reversed(messages):
        # LangChain HumanMessage 对象
        if hasattr(msg, "type") and msg.type == "human":
            user_message = msg.content
            break
        # 字典格式
        elif isinstance(msg, dict) and msg.get("role") == "user":
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

    # ========== 前置检测：系统控制意图（规则匹配，不走 LLM） ==========
    # 转人工、投诉、售后等系统控制意图优先级最高
    # 不经过业务分类器，直接拦截返回
    system_control = check_system_control(user_message)
    if system_control["is_system_control"]:
        print(f"[LangGraph] 前置检测命中系统控制意图：{system_control['type']}")
        return {
            "intent": INTENT_UNKNOWN,
            "confidence": 1.0,
            "role_name": "",
            "answer": system_control["message"],
            "sources": [],
            "hitl_required": True
        }

    # ========== 正常流程：LLM 意图分类（仅在未命中系统控制意图时） ==========
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


def hitl_checker_node(state: State) -> dict:
    """
    HITL 检测节点

    功能：
    - Agent 执行完后，检查是否需要人工介入
    - 如果需要，调用 interrupt() 暂停图执行，等待人工输入
    - 如果不需要，继续到 END

    检测条件：
    1. Agent 拒绝（回复包含拒绝关键词）
    2. 置信度低（confidence < 0.5）
    3. 敏感问题

    注意：会话快照在 web/app.py 中生成（因为 interrupt 后节点无法写入 state）

    Args:
        state: 当前对话状态

    Returns:
        更新后的状态字段
    """
    # 获取需要的信息
    answer = state.get("answer", "")
    messages = state.get("messages", [])
    confidence = state.get("confidence", 1.0)
    user_query = _get_last_user_message(state)

    # 综合判断是否需要转人工
    result = should_escalate_to_human(
        answer=answer,
        messages=messages,
        confidence=confidence,
        user_query=user_query
    )

    if result["needs_human"]:
        print(f"[HITL] 需要人工介入，原因：{result['reason']}")
        # 调用 interrupt() 暂停图执行，等待人工输入
        # interrupt() 返回后，图正常返回（不抛异常），web 层检测 hitl_required
        from langgraph.types import interrupt
        human_response = interrupt({
            "reason": result["reason"],
            "message": f"您的问题需要人工客服处理（原因：{result['reason']}）"
        })

        # 人工输入后，用人工的回答替换原来的回答
        return {
            "answer": human_response,
            "hitl_required": True
        }
    else:
        print(f"[HITL] 不需要人工介入")
        return {
            "hitl_required": False
        }


def _get_last_user_message(state: State) -> str:
    """
    从 State 中提取最新的用户消息

    兼容两种消息格式：
    - 字典格式：{"role": "user", "content": "..."}
    - LangChain 对象：HumanMessage(content="...")

    Args:
        state: 当前对话状态

    Returns:
        最新的用户消息文本
    """
    messages = state.get("messages", [])
    for msg in reversed(messages):
        # 兼容 LangChain HumanMessage 对象
        if hasattr(msg, "type") and msg.type == "human":
            return msg.content
        # 兼容字典格式
        elif isinstance(msg, dict) and msg.get("role") == "user":
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
