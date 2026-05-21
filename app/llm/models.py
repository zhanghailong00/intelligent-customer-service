"""
大语言模型封装模块
封装 DeepSeek API 调用，提供统一的对话接口
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    """
    获取 DeepSeek LLM 实例

    Args:
        temperature: 生成温度，越高越随机，越低越确定

    Returns:
        ChatOpenAI 实例
    """
    return ChatOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL,
        temperature=temperature
    )


def chat(messages: list, temperature: float = 0.7) -> str:
    """
    与 LLM 对话

    Args:
        messages: 消息列表，格式为 [{"role": "user/system", "content": "..."}]
        temperature: 生成温度

    Returns:
        LLM 生成的回复文本
    """
    llm = get_llm(temperature)

    # 将字典格式的消息转换为 LangChain 消息对象
    lc_messages = []
    for msg in messages:
        if msg["role"] == "system":
            lc_messages.append(SystemMessage(content=msg["content"]))
        elif msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))

    # 调用 LLM 生成回复
    response = llm.invoke(lc_messages)
    return response.content
