"""
大语言模型封装模块
封装 DeepSeek API 调用，提供统一的对话接口
支持 Fallback 机制：主模型异常时自动切换备用模型
支持流式输出：逐 token 返回，提升用户体验
"""
import time
from typing import Optional, Generator
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import (
    # 主模型配置（DeepSeek）
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    # 备用模型配置（通义千问）
    QWEN_LLM_API_KEY,
    QWEN_LLM_BASE_URL,
    QWEN_LLM_MODEL,
    # Fallback 配置
    LLM_PRIMARY_TIMEOUT,
    LLM_FALLBACK_TIMEOUT,
    LLM_FALLBACK_ENABLED
)


def get_llm(
    temperature: float = 0.7,
    provider: str = "primary",
    timeout: Optional[int] = None
) -> ChatOpenAI:
    """
    获取 LLM 实例

    Args:
        temperature: 生成温度，越高越随机，越低越确定
        provider: 提供商类型，"primary" 为 DeepSeek，"fallback" 为通义千问
        timeout: 超时时间（秒），None 使用默认值

    Returns:
        ChatOpenAI 实例
    """
    if provider == "fallback":
        # 备用模型：通义千问
        return ChatOpenAI(
            api_key=QWEN_LLM_API_KEY,
            base_url=QWEN_LLM_BASE_URL,
            model=QWEN_LLM_MODEL,
            temperature=temperature,
            timeout=timeout or LLM_FALLBACK_TIMEOUT
        )
    else:
        # 主模型：DeepSeek
        return ChatOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            model=DEEPSEEK_MODEL,
            temperature=temperature,
            timeout=timeout or LLM_PRIMARY_TIMEOUT
        )


def _call_llm(llm: ChatOpenAI, messages: list) -> str:
    """
    调用 LLM 生成回复

    Args:
        llm: ChatOpenAI 实例
        messages: LangChain 消息列表

    Returns:
        LLM 生成的回复文本
    """
    response = llm.invoke(messages)
    return response.content


def chat(messages: list, temperature: float = 0.7) -> str:
    """
    与 LLM 对话（支持 Fallback 机制）

    主模型调用失败时，自动切换到备用模型继续服务。

    Args:
        messages: 消息列表，格式为 [{"role": "user/system", "content": "..."}]
        temperature: 生成温度

    Returns:
        LLM 生成的回复文本
    """
    # 将字典格式的消息转换为 LangChain 消息对象
    lc_messages = []
    for msg in messages:
        if msg["role"] == "system":
            lc_messages.append(SystemMessage(content=msg["content"]))
        elif msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))

    # 获取主模型
    primary_llm = get_llm(temperature, provider="primary")

    # 尝试调用主模型
    try:
        start_time = time.time()
        result = _call_llm(primary_llm, lc_messages)
        elapsed = time.time() - start_time
        print(f"[LLM] 主模型 ({DEEPSEEK_MODEL}) 调用成功，耗时: {elapsed:.2f}s")
        return result
    except Exception as e:
        print(f"[LLM] 主模型 ({DEEPSEEK_MODEL}) 调用失败: {type(e).__name__}: {e}")

        # 如果未启用 Fallback 或是其他错误，直接抛出
        if not LLM_FALLBACK_ENABLED:
            raise

        # Fallback 到备用模型
        print(f"[LLM] 触发 Fallback，切换到备用模型 ({QWEN_LLM_MODEL})...")
        try:
            fallback_llm = get_llm(temperature, provider="fallback")
            start_time = time.time()
            result = _call_llm(fallback_llm, lc_messages)
            elapsed = time.time() - start_time
            print(f"[LLM] 备用模型 ({QWEN_LLM_MODEL}) 调用成功，耗时: {elapsed:.2f}s")
            return result
        except Exception as fallback_error:
            print(f"[LLM] 备用模型 ({QWEN_LLM_MODEL}) 也失败了: {type(fallback_error).__name__}: {fallback_error}")
            raise Exception(f"主模型和备用模型均调用失败。主模型错误: {e}，备用模型错误: {fallback_error}")


def chat_stream(messages: list, temperature: float = 0.7) -> Generator[str, None, None]:
    """
    与 LLM 对话（流式输出，支持 Fallback）

    使用 llm.stream() 逐 token 返回，提升用户体验。

    Args:
        messages: 消息列表，格式为 [{"role": "user/system", "content": "..."}]
        temperature: 生成温度

    Yields:
        LLM 生成的 token 文本
    """
    # 将字典格式的消息转换为 LangChain 消息对象
    lc_messages = []
    for msg in messages:
        if msg["role"] == "system":
            lc_messages.append(SystemMessage(content=msg["content"]))
        elif msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))

    # 获取主模型
    primary_llm = get_llm(temperature, provider="primary")

    # 尝试调用主模型（流式）
    try:
        start_time = time.time()
        token_count = 0
        for chunk in primary_llm.stream(lc_messages):
            if chunk.content:
                token_count += 1
                yield chunk.content
        elapsed = time.time() - start_time
        print(f"[LLM] 主模型 ({DEEPSEEK_MODEL}) 流式调用成功，耗时: {elapsed:.2f}s，tokens: {token_count}")
    except Exception as e:
        print(f"[LLM] 主模型 ({DEEPSEEK_MODEL}) 流式调用失败: {type(e).__name__}: {e}")

        # 如果未启用 Fallback，直接抛出
        if not LLM_FALLBACK_ENABLED:
            raise

        # Fallback 到备用模型
        print(f"[LLM] 触发 Fallback，切换到备用模型 ({QWEN_LLM_MODEL})...")
        try:
            fallback_llm = get_llm(temperature, provider="fallback")
            start_time = time.time()
            token_count = 0
            for chunk in fallback_llm.stream(lc_messages):
                if chunk.content:
                    token_count += 1
                    yield chunk.content
            elapsed = time.time() - start_time
            print(f"[LLM] 备用模型 ({QWEN_LLM_MODEL}) 流式调用成功，耗时: {elapsed:.2f}s，tokens: {token_count}")
        except Exception as fallback_error:
            print(f"[LLM] 备用模型 ({QWEN_LLM_MODEL}) 也失败了: {type(fallback_error).__name__}: {fallback_error}")
            raise Exception(f"主模型和备用模型均调用失败。主模型错误: {e}，备用模型错误: {fallback_error}")


def chat_with_fallback_status(messages: list, temperature: float = 0.7) -> dict:
    """
    与 LLM 对话，并返回详细的调用状态

    Args:
        messages: 消息列表
        temperature: 生成温度

    Returns:
        包含以下字段的字典：
        - answer: LLM 生成的回复
        - provider: 实际使用的模型提供商（"primary" 或 "fallback"）
        - model: 实际使用的模型名称
        - fallback_triggered: 是否触发了 Fallback
    """
    # 将字典格式的消息转换为 LangChain 消息对象
    lc_messages = []
    for msg in messages:
        if msg["role"] == "system":
            lc_messages.append(SystemMessage(content=msg["content"]))
        elif msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))

    # 尝试调用主模型
    try:
        primary_llm = get_llm(temperature, provider="primary")
        start_time = time.time()
        result = _call_llm(primary_llm, lc_messages)
        elapsed = time.time() - start_time
        print(f"[LLM] 主模型 ({DEEPSEEK_MODEL}) 调用成功，耗时: {elapsed:.2f}s")
        return {
            "answer": result,
            "provider": "primary",
            "model": DEEPSEEK_MODEL,
            "fallback_triggered": False
        }
    except Exception as e:
        print(f"[LLM] 主模型 ({DEEPSEEK_MODEL}) 调用失败: {type(e).__name__}: {e}")

        if not LLM_FALLBACK_ENABLED:
            raise

        # Fallback 到备用模型
        print(f"[LLM] 触发 Fallback，切换到备用模型 ({QWEN_LLM_MODEL})...")
        try:
            fallback_llm = get_llm(temperature, provider="fallback")
            start_time = time.time()
            result = _call_llm(fallback_llm, lc_messages)
            elapsed = time.time() - start_time
            print(f"[LLM] 备用模型 ({QWEN_LLM_MODEL}) 调用成功，耗时: {elapsed:.2f}s")
            return {
                "answer": result,
                "provider": "fallback",
                "model": QWEN_LLM_MODEL,
                "fallback_triggered": True
            }
        except Exception as fallback_error:
            print(f"[LLM] 备用模型 ({QWEN_LLM_MODEL}) 也失败了: {type(fallback_error).__name__}: {fallback_error}")
            raise Exception(f"主模型和备用模型均调用失败。主模型错误: {e}，备用模型错误: {fallback_error}")
