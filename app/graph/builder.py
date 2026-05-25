"""
LangGraph 图构建

功能：
- 构建对话状态图
- 定义节点和边的连接关系
- 编译生成可执行的 graph

状态图结构（Phase 5 HITL 后）：
    start → classifier_node →
      ├── greeting_node → END
      ├── unknown_node → END
      ├── product_agent_node → hitl_checker_node → END
      ├── fault_agent_node   → hitl_checker_node → END
      └── training_agent_node → hitl_checker_node → END

设计思路：
- classifier_node 是唯一的入口节点，负责意图分类
- 通过条件边（conditional_edges）根据 intent 路由到不同节点
- 每个 Agent 节点独立，方便后续扩展不同逻辑
- Agent 回答后经过 hitl_checker 检测，决定是否需要人工介入
- greeting/unknown 不需要 HITL 检测，直接到 END
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.graph.state import State
from app.graph.nodes import (
    classifier_node,
    greeting_node,
    unknown_node,
    product_agent_node,
    fault_agent_node,
    training_agent_node,
    hitl_checker_node,
    route_by_intent
)


def build_graph(checkpointer=None) -> StateGraph:
    """
    构建 LangGraph 状态图

    Args:
        checkpointer: 状态持久化器，HITL interrupt 需要配置 MemorySaver

    Returns:
        编译后的 StateGraph，可以直接调用 graph.invoke()
    """
    # 1. 创建状态图，指定 State 类型
    graph = StateGraph(State)

    # 2. 添加节点
    graph.add_node("classifier_node", classifier_node)
    graph.add_node("greeting_node", greeting_node)
    graph.add_node("unknown_node", unknown_node)
    graph.add_node("product_agent_node", product_agent_node)
    graph.add_node("fault_agent_node", fault_agent_node)
    graph.add_node("training_agent_node", training_agent_node)
    graph.add_node("hitl_checker_node", hitl_checker_node)

    # 3. 设置入口节点
    graph.set_entry_point("classifier_node")

    # 4. 添加条件边：classifier 根据 intent 路由到不同节点
    graph.add_conditional_edges(
        "classifier_node",      # 源节点
        route_by_intent,        # 路由函数
        {
            "greeting_node": "greeting_node",
            "unknown_node": "unknown_node",
            "product_agent_node": "product_agent_node",
            "fault_agent_node": "fault_agent_node",
            "training_agent_node": "training_agent_node",
        }
    )

    # 5. 添加普通边
    # greeting/unknown 直接结束（不需要 HITL 检测）
    graph.add_edge("greeting_node", END)
    graph.add_edge("unknown_node", END)

    # Agent 节点执行完后，进入 HITL 检测节点
    graph.add_edge("product_agent_node", "hitl_checker_node")
    graph.add_edge("fault_agent_node", "hitl_checker_node")
    graph.add_edge("training_agent_node", "hitl_checker_node")

    # HITL 检测节点执行完后结束
    # （如果需要人工介入，hitl_checker_node 内部会调用 interrupt() 暂停图）
    graph.add_edge("hitl_checker_node", END)

    # 6. 编译图（传入 checkpointer 支持 interrupt 暂停/恢复）
    compiled_graph = graph.compile(checkpointer=checkpointer)

    print("[LangGraph] 状态图构建完成")
    return compiled_graph


# 全局单例：编译后的 graph（避免重复构建）
_graph = None


def get_graph() -> StateGraph:
    """
    获取编译后的 LangGraph（单例模式）

    使用 MemorySaver 作为 checkpointer，支持 interrupt 暂停/恢复（HITL 机制）

    Returns:
        编译后的 StateGraph
    """
    global _graph
    if _graph is None:
        # 创建 MemorySaver 作为 checkpointer，支持 HITL interrupt
        _checkpointer = MemorySaver()
        _graph = build_graph(checkpointer=_checkpointer)
    return _graph
