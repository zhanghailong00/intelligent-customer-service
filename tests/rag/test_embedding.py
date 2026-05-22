"""
测试通义千问 Embedding API
使用 dashscope SDK 调用 tongyi-embedding-vision-flash 模型
"""
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dashscope
from app.config import QWEN_API_KEY

# 设置 API Key
dashscope.api_key = QWEN_API_KEY


def get_embedding(text: str) -> list:
    """
    获取文本的向量表示

    Args:
        text: 要向量化的文本

    Returns:
        向量列表
    """
    input_data = [{'text': text}]
    resp = dashscope.MultiModalEmbedding.call(
        model="tongyi-embedding-vision-flash-2026-03-06",
        input=input_data
    )
    return resp.output['embeddings'][0]['embedding']


# 测试
if __name__ == "__main__":
    test_text = "怎么安装VMware Workstation Pro"
    embedding = get_embedding(test_text)

    print("=" * 50)
    print("通义千问 Embedding API 测试")
    print("=" * 50)
    print(f"输入文本：{test_text}")
    print(f"向量维度：{len(embedding)}")
    print(f"前5个值：{embedding[:5]}")
    print("=" * 50)
