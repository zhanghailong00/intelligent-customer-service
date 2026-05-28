"""
Gradio 界面模块
提供简单的聊天界面，直接调用 LangGraph 状态图
支持流式输出：逐 token 显示回答，提升用户体验
启动命令：python web/app.py
"""
import os
import sys
import time

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import traceback
import gradio as gr
from app.graph.builder import get_graph
from app.llm.intent_classifier import get_intent_label
from langgraph.types import Command
from app.hitl.handoff import generate_snapshot, format_snapshot_display
from app.hitl.detector import check_agent_refusal, check_low_confidence, check_sensitive_content

# HITL 状态管理：记录待处理的 interrupt（简化版，单用户开发环境适用）
_pending_interrupt = None
_hitl_active = False  # HITL 是否激活（人工客服接管中）

# 流式输出配置
STREAM_DELAY = 0.02  # 每个 token 的延迟（秒），控制打字速度


def _stream_response(text: str):
    """
    将文本逐 token 输出（生成器函数）

    模拟打字效果，提升用户体验。

    Args:
        text: 要输出的完整文本

    Yields:
        逐 token 的文本片段
    """
    current = ""
    for char in text:
        current += char
        yield current
        time.sleep(STREAM_DELAY)


def chat(message, history):
    """
    聊天函数，调用 LangGraph 状态图获取回复（支持流式输出）

    流程：
    1. 如果 HITL 激活中 → 用户输入作为人工客服回复直接显示
    2. 如果 HITL 未激活 → 正常调用 LangGraph
    3. 如果触发 HITL → 显示快照，等待人工回复

    Args:
        message: 用户输入的消息
        history: 对话历史（Gradio 自动管理）

    Yields:
        逐 token 的回答文本
    """
    global _pending_interrupt, _hitl_active

    try:
        # 1. HITL 激活中：所有消息作为人工客服回复，直到人工说"关闭"
        if _hitl_active:
            print(f"[Gradio] 人工客服回复：{message}")
            # 人工说"关闭" → 退出 HITL 模式，恢复 AI
            if message.strip() in ["关闭", "结束", "退出", "close"]:
                _hitl_active = False
                _pending_interrupt = None
                yield "✅ 已退出人工客服模式，AI 客服继续为您服务。"
                return
            yield f"**[人工客服]** {message}"
            return

        # 2. 获取 LangGraph 状态图
        graph = get_graph()

        # 3. 正常流程：构建消息历史
        messages = _convert_history(history)
        messages.append({"role": "user", "content": message})

        print(f"[Gradio] 收到消息：{message}")
        print(f"[Gradio] 历史消息数：{len(messages)}")

        # 4. 调用 LangGraph（同步处理）
        config = {"configurable": {"thread_id": "default"}}
        result = graph.invoke(
            {
                "messages": messages,
                "intent": "",
                "confidence": 0.0,
                "role_name": "",
                "answer": "",
                "sources": [],
                "hitl_required": False
            },
            config=config
        )

        # 5. 在前端层检测 HITL（LangGraph interrupt 后 state 不更新，需手动检测）
        answer = result.get("answer", "")
        confidence = result.get("confidence", 1.0)
        messages_list = result.get("messages", [])

        hitl_reason = None
        if check_agent_refusal(answer):
            hitl_reason = "Agent 拒绝回答"
        elif check_low_confidence(confidence):
            hitl_reason = "置信度低"
        elif check_sensitive_content(answer):
            hitl_reason = "敏感问题"

        if hitl_reason:
            print(f"[Gradio] HITL 触发（前端检测），原因：{hitl_reason}")

            # 生成会话快照
            snapshot = generate_snapshot(
                messages=messages_list,
                answer=answer,
                sources=result.get("sources", []),
                hitl_reason=hitl_reason,
                confidence=confidence
            )

            # 激活 HITL 模式，等待人工回复
            _hitl_active = True

            # 返回格式化的转人工提示（含会话快照）
            response = "⏳ **需要人工介入**\n\n"
            response += "正在为您转接人工客服，请稍候...\n\n"
            response += format_snapshot_display(snapshot) + "\n\n"
            response += "请描述您的问题，人工客服将为您处理。\n\n"
            response += "_（人工客服输入「关闭」可退出人工模式，恢复 AI 服务）_"
            yield response
            return

        # 6. 正常输出（流式显示）
        response = _format_response(result)
        yield from _stream_response(response)

    except Exception as e:
        # 打印完整错误堆栈到终端，方便调试
        print(f"[Gradio] 错误：{type(e).__name__}: {e}")
        traceback.print_exc()
        yield f"错误：{str(e)}\n\n请检查 API 配置是否正确。"


def _format_response(result):
    """
    格式化 LangGraph 返回结果

    Args:
        result: LangGraph 调用结果字典

    Returns:
        格式化的回答文本
    """
    response = result.get("answer", "")

    # 添加参考来源
    if result.get("sources"):
        response += "\n\n---\n**参考来源：**\n"
        for i, source in enumerate(result["sources"], 1):
            response += f"{i}. {source}\n"

    # 添加 Agent 身份标签和意图信息
    role_name = result.get("role_name", "")
    intent = result.get("intent", "")
    intent_label = get_intent_label(intent) if intent else "未知"
    confidence = result.get("confidence", 0)
    if role_name:
        response += f"\n\n_[{role_name} | 意图：{intent_label}，置信度：{confidence:.0%}]_"
    else:
        response += f"\n\n_[意图：{intent_label}，置信度：{confidence:.0%}]_"

    return response


def _convert_history(history):
    """
    将 Gradio history 转换为 LangGraph messages 格式

    Gradio 5.x 格式：[["user msg", "assistant msg"], ...]
    Gradio 6.x 格式：[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
    LangGraph 格式：[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]

    Args:
        history: Gradio 的对话历史

    Returns:
        LangGraph 兼容的消息列表
    """
    messages = []
    for item in history:
        # Gradio 6.x：字典格式 {"role": "user", "content": "..."}
        if isinstance(item, dict):
            role = item.get("role", "")
            content = item.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        # Gradio 5.x：列表格式 ["user msg", "assistant msg"]
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            if item[0]:
                messages.append({"role": "user", "content": item[0]})
            if item[1]:
                messages.append({"role": "assistant", "content": item[1]})
    return messages


# 创建 Gradio 聊天界面（支持流式输出）
demo = gr.ChatInterface(
    fn=chat,
    title="实训设备智能客服",
    description="基于多 Agent 的实训设备智能客服，自动识别问题类型并由专业 Agent 回答。",
    examples=[
        "如何搭建实验环境？",
        "输入输出设备怎么选择？",
        "传感器不亮了怎么办？",
        "怎么做实验？",
    ]
)

if __name__ == "__main__":
    print("=" * 60)
    print("智科云联 - 实训设备智能客服")
    print("=" * 60)
    print(f"项目根目录：{PROJECT_ROOT}")
    print("启动 Gradio 界面...")
    print("访问地址：http://localhost:7860")
    print("=" * 60)

    # 启动 Gradio 服务
    demo.launch(
        server_name="127.0.0.1",
        server_port=7888,
        share=False  # 不生成公网链接，仅本地访问
    )
