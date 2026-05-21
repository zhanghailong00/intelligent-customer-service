"""
向量存储模块
负责将文档 chunks 向量化并存入 ChromaDB
"""
import os
import sys
import time
from typing import List, Dict

import chromadb
import dashscope

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from app.config import (
    QWEN_API_KEY,
    QWEN_EMBEDDING_MODEL,
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME
)

# 设置 dashscope API Key
dashscope.api_key = QWEN_API_KEY


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    批量获取文本的向量表示

    Args:
        texts: 文本列表

    Returns:
        向量列表
    """
    # dashscope 每次最多处理 25 条
    batch_size = 25
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        input_data = [{'text': text} for text in batch]

        resp = dashscope.MultiModalEmbedding.call(
            model=QWEN_EMBEDDING_MODEL,
            input=input_data
        )

        if resp.status_code != 200:
            raise Exception(f"Embedding API 调用失败: {resp.message}")

        batch_embeddings = [item['embedding'] for item in resp.output['embeddings']]
        all_embeddings.extend(batch_embeddings)

        # 避免 API 限流
        if i + batch_size < len(texts):
            time.sleep(0.5)

    return all_embeddings


def get_vectorstore():
    """
    获取 ChromaDB 向量数据库实例

    Returns:
        ChromaDB Client 和 Collection
    """
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
    )
    return client, collection


def add_documents(chunks: List[Dict]) -> int:
    """
    将切分后的 chunks 向量化并存入 ChromaDB

    Args:
        chunks: 切分后的 chunk 列表，每个 chunk 包含 content 和 metadata

    Returns:
        成功存储的文档数量
    """
    if not chunks:
        print("没有需要存储的文档")
        return 0

    print(f"开始向量化 {len(chunks)} 个文档...")

    # 1. 提取文本内容
    texts = [chunk['content'] for chunk in chunks]

    # 2. 批量获取向量
    print("调用通义千问 Embedding API...")
    embeddings = get_embeddings(texts)
    print(f"向量化完成，向量维度: {len(embeddings[0])}")

    # 3. 准备 ChromaDB 数据
    ids = [f"chunk_{i:04d}" for i in range(len(chunks))]
    documents = texts
    metadatas = [chunk['metadata'] for chunk in chunks]

    # 4. 存入 ChromaDB
    print("存入 ChromaDB...")
    client, collection = get_vectorstore()

    # 清空旧数据（如果需要）
    # collection.delete(where={})

    # 批量插入
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )

    print(f"存储完成，共 {len(chunks)} 个文档")
    return len(chunks)


def clear_vectorstore():
    """
    清空向量数据库

    Returns:
        是否成功
    """
    try:
        client, collection = get_vectorstore()
        client.delete_collection(CHROMA_COLLECTION_NAME)
        print("向量数据库已清空")
        return True
    except Exception as e:
        print(f"清空失败: {e}")
        return False


def get_vectorstore_stats() -> Dict:
    """
    获取向量数据库统计信息

    Returns:
        统计信息
    """
    try:
        client, collection = get_vectorstore()
        count = collection.count()
        return {
            "collection": CHROMA_COLLECTION_NAME,
            "count": count,
            "persist_dir": CHROMA_PERSIST_DIR
        }
    except Exception as e:
        return {"error": str(e)}
