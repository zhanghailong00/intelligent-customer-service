"""
LangGraph 基础框架测试脚本

测试内容：
1. 状态图是否能正常构建
2. 意图分类是否正确
3. 路由是否正确（greeting/unknown/product/fault/training）
4. Agent 是否能正常调用
5. 对话历史是否能正确传递
"""
import sys
import os

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from app.graph.builder import get_graph


def test_single_query(query: str):
    """测试单个查询"""
    print(f"\n{'='*60}")
    print(f"用户问题：{query}")
    print(f"{'='*60}")

    graph = get_graph()

    # 调用 LangGraph
    result = graph.invoke({
        "messages": [{"role": "user", "content": query}],
        "intent": "",
        "confidence": 0.0,
        "role_name": "",
        "answer": "",
        "sources": [],
        "hitl_required": False
    })

    # 输出结果
    print(f"意图：{result.get('intent', '未知')}")
    print(f"置信度：{result.get('confidence', 0):.2f}")
    print(f"角色：{result.get('role_name', '无')}")
    print(f"回答：{result.get('answer', '无')}")
    if result.get('sources'):
        print(f"来源：{result['sources']}")
    print()


def test_multi_turn():
    """测试多轮对话（对话历史传递）"""
    print(f"\n{'='*60}")
    print("多轮对话测试")
    print(f"{'='*60}")

    graph = get_graph()

    # 第一轮
    print("\n--- 第 1 轮 ---")
    result1 = graph.invoke({
        "messages": [{"role": "user", "content": "这个箱子有什么功能？"}],
        "intent": "",
        "confidence": 0.0,
        "role_name": "",
        "answer": "",
        "sources": [],
        "hitl_required": False
    })
    print(f"用户：这个箱子有什么功能？")
    print(f"意图：{result1['intent']}，角色：{result1['role_name']}")
    print(f"回答：{result1['answer'][:100]}...")

    # 第二轮（带历史）
    print("\n--- 第 2 轮 ---")
    # 构建历史消息
    messages = [
        {"role": "user", "content": "这个箱子有什么功能？"},
        {"role": "assistant", "content": result1["answer"]}
    ]
    result2 = graph.invoke({
        "messages": messages + [{"role": "user", "content": "那它的价格呢？"}],
        "intent": "",
        "confidence": 0.0,
        "role_name": "",
        "answer": "",
        "sources": [],
        "hitl_required": False
    })
    print(f"用户：那它的价格呢？")
    print(f"意图：{result2['intent']}，角色：{result2['role_name']}")
    print(f"回答：{result2['answer'][:100]}...")


if __name__ == "__main__":
    # 测试用例
    test_queries = [
        "你好",                    # greeting
        "这个箱子有什么功能？",     # product
        "传感器不亮了",            # fault
        "有课件吗？",              # training
        "今天天气怎么样？",         # unknown
    ]

    print("=" * 60)
    print("LangGraph 基础框架测试")
    print("=" * 60)

    # 单轮测试
    for query in test_queries:
        test_single_query(query)

    # 多轮测试
    test_multi_turn()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
