"""
向量检索模块
负责与 ChromaDB 向量数据库交互，执行语义检索
"""
import chromadb
from app.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, RETRIEVAL_TOP_K


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


def retrieve(query: str, top_k: int = RETRIEVAL_TOP_K) -> list:
    """
    根据查询文本检索最相关的文档

    Args:
        query: 用户查询文本
        top_k: 返回的最相关文档数量

    Returns:
        相关文档列表
    """
    collection = get_vectorstore()

    # 执行向量相似度检索
    results = collection.query(
        query_texts=[query],  # 查询文本
        n_results=top_k       # 返回数量
    )

    # 返回检索到的文档内容
    return results["documents"][0] if results["documents"] else []
