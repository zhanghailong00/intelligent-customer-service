"""
Query Rewriting 模块（查询改写）

功能：
- 在 RAG 检索前改写用户问题
- 补充缺失上下文、消除模糊指代、扩展关键词
- 提升向量检索的召回率和准确率

技术路线：
- LLM 改写：用 DeepSeek 分析问题并重写
- 降级机制：改写失败时返回原始 query

使用位置：
- Agent.run() 中，retrieve() 之前调用
- 只用于检索，不影响意图分类和 HITL 检测
"""
from app.llm.models import chat


# 改写 Prompt
REWRITE_PROMPT = """你是一个查询优化专家。请将用户问题改写为更适合知识库检索的形式。

当前场景：{context}

改写要求：
1. 补充缺失的上下文（设备名称、场景等）
2. 消除代词和模糊指代（"这个"、"那个"、"它"）
3. 扩展关键词，让问题更具体
4. 保持原意，不要改变问题方向
5. 输出改写后的问题，不要解释

示例：
- "不亮了" → "温湿度传感器指示灯不亮如何排查故障"
- "怎么搭" → "如何搭建嵌入式实验环境"
- "那个报错" → "运行程序时出现错误的解决方法"

用户问题：{query}
改写后："""


def rewrite_query(query: str, context: str = "") -> str:
    """
    查询改写

    将用户问题改写为更适合向量检索的形式。

    Args:
        query: 原始用户问题
        context: 场景上下文（如"产品专家"、"故障排查"、"培训指导"）

    Returns:
        改写后的问题，改写失败时返回原始 query
    """
    # 空 query 直接返回
    if not query or not query.strip():
        return query

    print(f"[Rewriter] 原始 query：{query}")

    try:
        # 调用 LLM 改写
        response = chat(
            messages=[
                {"role": "system", "content": REWRITE_PROMPT.format(
                    context=context or "通用客服场景",
                    query=query
                )}
            ],
            temperature=0.3  # 低温度，确保输出稳定
        )

        rewritten = response.strip()

        # 验证：改写结果不能为空，且不能与原始 query 完全相同（超过一定长度时）
        if rewritten and len(rewritten) > 0:
            print(f"[Rewriter] 改写后：{rewritten}")
            return rewritten
        else:
            print(f"[Rewriter] 改写结果为空，使用原始 query")
            return query

    except Exception as e:
        print(f"[Rewriter] 改写失败：{e}，使用原始 query")
        return query
