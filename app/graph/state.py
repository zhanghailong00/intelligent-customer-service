"""
LangGraph 状态定义

功能：
- 定义整个对话流程的共享状态
- 所有节点（意图分类、Agent 执行等）读写同一个 State
- 使用 Annotated[list, add_messages] 自动管理消息追加

设计思路：
- messages 字段由 LangGraph 自动管理，支持对话记忆
- 其他字段在各节点间传递中间结果
- hitl_required 预留给 Phase 5 的人工介入
"""
from typing import TypedDict, Annotated, List
from langgraph.graph import add_messages


class State(TypedDict):
    """
    LangGraph 对话状态

    所有节点共享这个状态对象，每个节点读取需要的字段、写入自己的输出。
    """

    # 对话历史（LangGraph 自动管理追加/合并）
    # Annotated[list, add_messages] 让 LangGraph 知道如何合并多处写入的 messages
    messages: Annotated[list, add_messages]

    # 意图分类结果（classifier 节点写入）
    intent: str          # 意图类型：product/fault/training/greeting/unknown

    # 意图分类置信度（classifier 节点写入）
    confidence: float    # 0.0 - 1.0

    # Agent 身份名称（classifier 节点写入，用于 UI 显示）
    role_name: str       # 产品专家 / 技术支持 / 培训顾问

    # 生成的回答（agent 节点或 greeting/unknown 节点写入）
    answer: str

    # 参考来源（agent 节点写入）
    sources: List[str]

    # 是否需要人工介入（预留 Phase 5）
    hitl_required: bool
