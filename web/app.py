"""
Gradio 界面模块
提供 Web 聊天界面，调用后端 API
启动命令：python web/app.py
"""
import gradio as gr
import requests

# 后端 API 地址
API_URL = "http://localhost:8000/api/chat"


def chat(message, history):
    """
    聊天函数，调用后端 API 获取回复

    Args:
        message: 用户输入的消息
        history: 对话历史

    Returns:
        LLM 生成的回复
    """
    try:
        # 发送请求到后端 API
        response = requests.post(API_URL, json={
            "message": message,
            "history": history
        })
        result = response.json()
        return result["reply"]
    except Exception as e:
        return f"错误：{str(e)}"


# 创建 Gradio 聊天界面
demo = gr.ChatInterface(
    fn=chat,
    title="智能客服系统",
    description="基于 RAG 的实训设备智能客服",
    examples=[
        "怎么安装VMware",
        "智慧农业实训箱有什么模块",
        "设备不工作了怎么办"
    ],
    theme=gr.themes.Soft()
)

if __name__ == "__main__":
    # 启动 Gradio 服务
    demo.launch(server_name="0.0.0.0", server_port=7860)
