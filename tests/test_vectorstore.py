"""
测试向量化存储模块
验证文档向量化并存入 ChromaDB 的流程
"""
import os
import sys
import time

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.rag.loader import load_and_split
from app.rag.vectorstore import add_documents, clear_vectorstore, get_vectorstore_stats

# 测试文件路径
file_path = os.path.join(PROJECT_ROOT, "data", "processed", "02-实验环境的搭建.md")

print("=" * 60)
print("向量化存储测试")
print("=" * 60)

# 1. 检查文件是否存在
if not os.path.exists(file_path):
    print(f"错误: 文件不存在 - {file_path}")
    sys.exit(1)

# 2. 加载并切分文档
print(f"\n1. 加载文档: {file_path}")
chunks = load_and_split(file_path)
print(f"   切分为 {len(chunks)} 个 chunk")

# 3. 清空旧数据
print("\n2. 清空旧的向量数据...")
clear_vectorstore()

# 4. 向量化并存储
print("\n3. 向量化并存储...")
start_time = time.time()
count = add_documents(chunks)
elapsed_time = time.time() - start_time
print(f"   耗时: {elapsed_time:.2f} 秒")

# 5. 查看统计信息
print("\n4. 向量数据库统计:")
stats = get_vectorstore_stats()
for key, value in stats.items():
    print(f"   {key}: {value}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
