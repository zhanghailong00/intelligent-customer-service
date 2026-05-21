"""
测试向量检索模块
验证基于相似度的文档检索功能
"""
import os
import sys

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.rag.retriever import retrieve, retrieve_with_context, get_retrieval_stats

print("=" * 60)
print("向量检索测试")
print("=" * 60)

# 1. 查看统计信息
print("\n1. 向量数据库统计:")
stats = get_retrieval_stats()
for key, value in stats.items():
    print(f"   {key}: {value}")

# 2. 测试基本检索
print("\n2. 测试基本检索:")
test_queries = [
    "如何搭建实验环境",
    "Python 安装",
    "网络配置"
]

for query in test_queries:
    print(f"\n   查询: {query}")
    results = retrieve(query, top_k=2)
    print(f"   找到 {len(results)} 个相关文档")
    for i, result in enumerate(results, 1):
        score = result.get("score", "N/A")
        source = result["metadata"].get("source", "未知")
        chapter = result["metadata"].get("chapter", "未知")
        print(f"     {i}. 相似度: {score} | 来源: {source} | 章节: {chapter}")
        print(f"        内容预览: {result['content'][:80]}...")

# 3. 测试元数据过滤
print("\n3. 测试元数据过滤:")
filters = {"source": "02-实验环境的搭建.md"}
results = retrieve("环境", filters=filters, top_k=2)
print(f"   过滤条件: {filters}")
print(f"   找到 {len(results)} 个相关文档")
for i, result in enumerate(results, 1):
    score = result.get("score", "N/A")
    print(f"     {i}. 相似度: {score}")

# 4. 测试格式化上下文
print("\n4. 测试格式化上下文 (RAG 用):")
query = "如何安装 Python"
context = retrieve_with_context(query, top_k=2)
print(f"   查询: {query}")
print(f"   格式化上下文:")
print("-" * 40)
print(context[:500])
print("-" * 40)

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
