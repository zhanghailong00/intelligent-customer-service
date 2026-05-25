"""
Gradio 界面模块
提供简单的聊天界面，直接调用 LangGraph 状态图
启动命令：python web/app.py
"""
import os
import sys

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import traceback
import gradio as gr
from app.graph.builder import get_graph
from app.llm.intent_classifier import get_intent_label
from langgraph.errors import Interrupt
from langgraph.types import Command

# HITL 状态管理：记录待处理的 interrupt（简化版，单用户开发环境适用）
_pending_interrupt = None


def chat(message, history):
    """
    聊天函数，调用 LangGraph 状态图获取回复

    流程：
    1. 构建消息历史
    2. LangGraph（意图分类 → Agent 执行 → HITL 检测）
    3. 如果触发 interrupt（需要人工介入），显示提示并等待用户回复
    4. 格式化输出

    Args:
        message: 用户输入的消息
        history: 对话历史（Gradio 自动管理）

    Returns:
        格式化的回答
    """
    global _pending_interrupt

    try:
        # 1. 获取 LangGraph 状态图
        graph = get_graph()

        # 2. 如果有待处理的 interrupt，用用户输入恢复图执行
        if _pending_interrupt is not None:
            print(f"[Gradio] 恢复 HITL，人工回复：{message}")
            try:
                result = graph.invoke(
                    Command(resume=message),
                    config=_pending_interrupt["config"]
                )
                _pending_interrupt = None
                return _format_response(result)
            except Exception as resume_error:
                print(f"[Gradio] HITL 恢复失败：{resume_error}")
                _pending_interrupt = None
                return f"HITL 恢复失败：{str(resume_error)}"

        # 3. 正常流程：构建消息历史
        messages = _convert_history(history)
        messages.append({"role": "user", "content": message})

        print(f"[Gradio] 收到消息：{message}")
        print(f"[Gradio] 历史消息数：{len(messages)}")

        # 4. 调用 LangGraph
        config = {"configurable": {"thread_id": "default"}}
        try:
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
        except Interrupt as e:
            # 触发 HITL interrupt，图执行暂停
            interrupt_value = e.args[0] if e.args else {}
            reason = interrupt_value.get("reason", "未知原因")
            original_answer = interrupt_value.get("original_answer", "")

            print(f"[Gradio] HITL 触发，原因：{reason}")

            # 保存 interrupt 状态，等待用户回复
            _pending_interrupt = {"config": config}

            # 返回格式化的转人工提示
            response = f"⏳ **需要人工介入**\n\n"
            if original_answer:
                response += f"AI 原始回答：{original_answer}\n\n"
            response += f"**转人工原因**：{reason}\n\n"
            response += "---\n请直接输入您的回复，系统将用您的输入替代 AI 回答。"
            return response

        # 5. 格式化输出
        return _format_response(result)

    except Exception as e:
        # 打印完整错误堆栈到终端，方便调试
        print(f"[Gradio] 错误：{type(e).__name__}: {e}")
        traceback.print_exc()
        return f"错误：{str(e)}\n\n请检查 API 配置是否正确。"


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

    # 添加 HITL 标记
    if result.get("hitl_required"):
        response += "\n\n_[人工介入处理]_"

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


# 创建 Gradio 聊天界面（最简配置，兼容 Gradio 6.x）
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
        server_port=7860,
        share=False  # 不生成公网链接，仅本地访问
    )
