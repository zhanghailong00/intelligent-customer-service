"""
测试 RAG 问答链模块
验证检索 + LLM 生成回答的完整流程
"""
import os
import sys

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.rag.qa_chain import answer, format_answer_with_references

print("=" * 60)
print("RAG 问答链测试")
print("=" * 60)

# 测试问题列表
test_questions = [
    "如何搭建实验环境？",
    "输入输出设备选择？",
    "启动实验平台？",
    "这个系统支持哪些编程语言？"  # 这个问题知识库可能没有
]

for i, question in enumerate(test_questions, 1):
    print(f"\n{'=' * 60}")
    print(f"测试 {i}: {question}")
    print('=' * 60)

    # 调用 RAG 问答
    result = answer(question, top_k=3)

    # 格式化输出
    formatted = format_answer_with_references(result)
    print(formatted)

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
