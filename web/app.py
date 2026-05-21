"""
Gradio 界面模块
提供简单的聊天界面，直接调用 RAG 问答链
启动命令：python web/app.py
"""
import os
import sys

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import gradio as gr
from app.rag.qa_chain import answer, format_answer_with_references


def chat(message, history):
    """
    聊天函数，调用 RAG 问答链获取回复

    Args:
        message: 用户输入的消息
        history: 对话历史（Gradio 自动管理）

    Returns:
        格式化的回答（包含参考来源）
    """
    try:
        # 调用 RAG 问答链
        result = answer(message, top_k=3)

        # 格式化输出（包含参考来源）
        response = format_answer_with_references(result)

        return response
    except Exception as e:
        return f"错误：{str(e)}\n\n请检查 API 配置是否正确。"


# 创建 Gradio 聊天界面（最简配置，兼容 Gradio 6.x）
demo = gr.ChatInterface(
    fn=chat,
    title="智科云联 - 实训设备智能客服",
    description="基于 RAG 的实训设备智能客服助手，可以回答环境搭建、设备使用、故障排查等问题。",
    examples=[
        "如何搭建实验环境？",
        "输入输出设备怎么选择？",
        "怎么启动实验平台？",
        "这个系统支持哪些编程语言？"
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
