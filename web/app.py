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
from app.graph.router import route


def chat(message, history):
    """
    聊天函数，调用多 Agent 路由获取回复

    流程：意图分类 → 选择 Agent → 检索 → 生成回答

    Args:
        message: 用户输入的消息
        history: 对话历史（Gradio 自动管理）

    Returns:
        格式化的回答（包含参考来源和意图信息）
    """
    try:
        # 调用多 Agent 路由
        result = route(message)

        # 格式化输出
        response = result["answer"]

        # 添加参考来源
        if result.get("sources"):
            response += "\n\n---\n**参考来源：**\n"
            for i, source in enumerate(result["sources"], 1):
                response += f"{i}. {source}\n"

        # 添加 Agent 身份标签和意图信息
        role_name = result.get("role_name", "")
        intent_label = result.get("intent_label", "未知")
        confidence = result.get("confidence", 0)
        if role_name:
            response += f"\n\n_[{role_name} | 意图：{intent_label}，置信度：{confidence:.0%}]_"
        else:
            response += f"\n\n_[意图：{intent_label}，置信度：{confidence:.0%}]_"

        return response
    except Exception as e:
        return f"错误：{str(e)}\n\n请检查 API 配置是否正确。"


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
