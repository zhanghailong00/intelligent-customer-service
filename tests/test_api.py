"""
API 测试脚本
测试 DeepSeek LLM 是否能正常调用
"""
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm.models import chat

# 测试 DeepSeek API
messages = [
    {"role": "user", "content": "你好，请介绍一下你自己"}
]

# 调用 LLM
response = chat(messages)

# 打印结果
print("=" * 50)
print("DeepSeek API 测试结果：")
print("=" * 50)
print(response)
print("=" * 50)
