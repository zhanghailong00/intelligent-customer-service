"""
测试文档加载和切分模块
验证 Markdown 按标题切分的效果
"""
import os
import sys

# 获取项目根目录（tests 的上一级目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 添加项目根目录到 Python 路径
sys.path.insert(0, PROJECT_ROOT)

from app.rag.loader import load_and_split

# 测试文件路径（使用绝对路径）
file_path = os.path.join(PROJECT_ROOT, "data", "processed", "02-实验环境的搭建.md")

print("=" * 60)
print("文档切分测试")
print("=" * 60)
print(f"文件: {file_path}")
print("=" * 60)

# 检查文件是否存在
if not os.path.exists(file_path):
    print(f"错误: 文件不存在 - {file_path}")
    sys.exit(1)

# 加载并切分
chunks = load_and_split(file_path)

# 显示切分结果
print(f"\n共切分为 {len(chunks)} 个 chunk\n")

for i, chunk in enumerate(chunks, 1):
    print(f"{'=' * 60}")
    print(f"Chunk {i}:")
    print(f"{'=' * 60}")
    print(f"元数据:")
    print(f"  来源: {chunk['metadata']['source']}")
    print(f"  章节: {chunk['metadata']['chapter']}")
    print(f"  上级: {chunk['metadata']['parent_chapter']}")
    print(f"  级别: {'#' * chunk['metadata']['level']}")
    print(f"\n内容预览 (前 200 字符):")
    print("-" * 40)
    print(chunk["content"][:200])
    print("-" * 40)
    print()
