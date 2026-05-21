"""
向量检索模块
负责与 ChromaDB 向量数据库交互，执行语义检索
支持返回文档内容、元数据、相似度分数，以及元数据过滤
查询时使用通义千问 Embedding API 保持与存储一致
"""
import chromadb
from typing import List, Dict, Optional
from app.config import (
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
    RETRIEVAL_TOP_K,
    QWEN_API_KEY,
    QWEN_EMBEDDING_MODEL
)
import dashscope

# 设置 dashscope API Key
dashscope.api_key = QWEN_API_KEY

# 相似度阈值：低于此分数的结果不返回（0-1，越高越相似）
SIMILARITY_THRESHOLD = 0.5


def get_query_embedding(text: str) -> List[float]:
    """
    使用通义千问 API 获取查询文本的向量表示

    Args:
        text: 查询文本

    Returns:
        向量（768 维）
    """
    input_data = [{'text': text}]
    resp = dashscope.MultiModalEmbedding.call(
        model=QWEN_EMBEDDING_MODEL,
        input=input_data
    )

    if resp.status_code != 200:
        raise Exception(f"Embedding API 调用失败: {resp.message}")

    return resp.output['embeddings'][0]['embedding']


def get_vectorstore():
    """
    获取 ChromaDB 向量数据库实例

    Returns:
        ChromaDB Collection 对象
    """
    # 创建持久化客户端，数据保存在本地磁盘
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    # 获取或创建集合（类似于数据库中的表）
    return client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)


def retrieve(
    query: str,
    top_k: int = RETRIEVAL_TOP_K,
    filters: Optional[Dict] = None,
    include_scores: bool = True
) -> List[Dict]:
    """
    根据查询文本检索最相关的文档

    Args:
        query: 用户查询文本
        top_k: 返回的最相关文档数量
        filters: 元数据过滤条件，格式如 {"source": "xxx.md"}
        include_scores: 是否包含相似度分数

    Returns:
        检索结果列表，每个结果包含：
        - content: 文档内容
        - metadata: 元数据（source, chapter, parent_chapter, level）
        - score: 相似度分数（可选）
    """
    collection = get_vectorstore()

    # 使用通义千问 API 向量化查询文本（保持与存储一致）
    query_embedding = get_query_embedding(query)

    # 构建查询参数
    query_params = {
        "query_embeddings": [query_embedding],  # 使用向量查询而非文本
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"]
    }

    # 添加元数据过滤（如果有）
    if filters:
        query_params["where"] = filters

    # 执行向量相似度检索
    results = collection.query(**query_params)

    # 解析结果
    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []
    distances = results["distances"][0] if results["distances"] else []

    # 组装返回结果
    retrieval_results = []
    for i, doc in enumerate(documents):
        # ChromaDB 返回的是距离（越小越相似），转换为相似度分数（0-1，越大越相似）
        # 使用余弦距离时，相似度 = 1 - 距离/2
        distance = distances[i] if i < len(distances) else 0
        similarity = max(0, 1 - distance / 2)

        # 过滤低于阈值的结果
        if similarity < SIMILARITY_THRESHOLD:
            continue

        result = {
            "content": doc,
            "metadata": metadatas[i] if i < len(metadatas) else {}
        }

        # 可选：包含相似度分数
        if include_scores:
            result["score"] = round(similarity, 4)

        retrieval_results.append(result)

    return retrieval_results


def retrieve_with_context(query: str, top_k: int = RETRIEVAL_TOP_K) -> str:
    """
    检索并格式化为 RAG 上下文字符串

    将检索结果格式化为适合 LLM 的上下文，用于构建 prompt

    Args:
        query: 用户查询文本
        top_k: 返回的最相关文档数量

    Returns:
        格式化的上下文字符串
    """
    results = retrieve(query, top_k=top_k, include_scores=False)

    if not results:
        return "未找到相关文档内容。"

    # 格式化上下文
    context_parts = []
    for i, result in enumerate(results, 1):
        metadata = result["metadata"]
        source = metadata.get("source", "未知来源")
        chapter = metadata.get("chapter", "未知章节")

        context_parts.append(
            f"【文档 {i}】来源：{source} | 章节：{chapter}\n{result['content']}"
        )

    return "\n\n".join(context_parts)


def get_retrieval_stats() -> Dict:
    """
    获取检索模块统计信息

    Returns:
        统计信息字典
    """
    try:
        collection = get_vectorstore()
        count = collection.count()
        return {
            "collection": CHROMA_COLLECTION_NAME,
            "document_count": count,
            "similarity_threshold": SIMILARITY_THRESHOLD,
            "persist_dir": CHROMA_PERSIST_DIR
        }
    except Exception as e:
        return {"error": str(e)}
