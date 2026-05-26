# 面试亮点：Query Rewriting 查询改写

---

## 一、问题背景

### 1.1 RAG 检索的痛点

用户提问可能表述模糊、缺少上下文，直接用于向量检索效果差：

| 用户原始提问 | 问题 |
|-------------|------|
| "不亮了" | 缺少主语，不知道是什么不亮 |
| "怎么搭" | 省略了宾语，不知道搭什么 |
| "那个报错" | 模糊指代，不知道具体报错信息 |

### 1.2 目标

在 RAG 检索前，用 LLM 将用户问题改写为更适合检索的形式，提升召回率。

---

## 二、方案设计

### 2.1 技术选型

| 方案 | 效果 | 延迟 | 成本 | 选择 |
|------|------|------|------|------|
| LLM 改写 | ⭐⭐⭐⭐⭐ | 高 | 高 | ✅ 选用 |
| HyDE | ⭐⭐⭐⭐ | 高 | 高 | 备选 |
| Query 分解 | ⭐⭐⭐⭐⭐ | 很高 | 很高 | 不需要 |
| 规则改写 | ⭐⭐ | 低 | 无 | 效果不够 |

选择 LLM 改写的理由：项目已有 DeepSeek API，实现简单，效果好。

### 2.2 作用范围设计

```
用户提问
    ↓
classifier_node（意图分类）  ← 用原始 query，不改写
    ↓
Agent 节点
    ├── rewrite_query()      ← 这里改写
    ├── retrieve(rewritten)  ← 用改写后 query 检索
    └── chat(original)       ← 用原始 query 生成回答
    ↓
hitl_checker_node（HITL 检测）← 用原始 query，不改写
```

**核心原则**：改写只用于检索，不影响意图识别和 HITL 检测。

**为什么不改写 HITL？**
- HITL 关键词匹配依赖原始表述（"转人工"不能改写为"用户想要转接人工客服"）
- 改写会增加不必要的开销

### 2.3 角色感知改写

不同 Agent 有不同的改写上下文：

| Agent | 角色 | 改写方向 |
|-------|------|---------|
| ProductAgent | 产品专家 | 补充产品名称、型号、功能参数 |
| FaultAgent | 故障排查 | 补充故障现象、设备名称、错误信息 |
| TrainingAgent | 培训指导 | 补充实验名称、课程内容 |

---

## 三、技术实现

### 3.1 模块设计

```
app/query/
├── __init__.py
└── rewriter.py  # 查询改写模块
```

### 3.2 核心代码

```python
REWRITE_PROMPT = """你是一个查询优化专家。请将用户问题改写为更适合知识库检索的形式。

当前场景：{context}

改写要求：
1. 补充缺失的上下文（设备名称、场景等）
2. 消除代词和模糊指代
3. 扩展关键词，让问题更具体
4. 保持原意，不要改变问题方向
5. 输出改写后的问题，不要解释

用户问题：{query}
改写后："""

def rewrite_query(query: str, context: str = "") -> str:
    """查询改写，失败时返回原始 query"""
    try:
        response = chat(messages=[...], temperature=0.3)
        return response.strip()
    except:
        return query  # 降级
```

### 3.3 调用位置

```python
# app/agents/base.py
def run(self, user_query, messages=None, top_k=3):
    # 1. 查询改写
    rewritten_query = rewrite_query(user_query, self.role_name)

    # 2. 用改写后 query 检索
    retrieval_results = retrieve(rewritten_query, top_k=top_k)

    # 3. 后续用原始 query
    context = self._build_context(retrieval_results)
    llm_messages = self._build_messages(user_query, context, messages)
    answer = chat(llm_messages)
```

---

## 四、面试话术

### 4.1 项目描述

> "RAG 系统的一个常见问题是用户表述模糊，直接检索效果差。我实现了 Query Rewriting 模块，用 LLM 在检索前改写用户问题，补充上下文、消除歧义。改写只用于检索，不影响意图识别和 HITL 检测。"

### 4.2 技术细节

> "改写 Prompt 设计了四个要求：补充上下文、消除指代、扩展关键词、保持原意。不同 Agent 有不同的改写上下文——产品 Agent 补充型号参数，故障 Agent 补充故障现象。改写失败时有降级机制，返回原始 query，不影响系统稳定性。"

### 4.3 延伸讨论

| 面试官可能问 | 可以聊的方向 |
|-------------|-------------|
| 改写效果怎么评估？ | 对比改写前后的检索召回率、回答准确率 |
| 为什么不只用 HyDE？ | HyDE 适合答案格式固定的场景，LLM 改写更通用 |
| 改写延迟怎么优化？ | 可以缓存常见改写、用更小的模型 |
| 改写失败怎么办？ | 降级机制，返回原始 query |

---

## 五、一句话总结

> "LLM 在检索前改写用户问题，补充上下文、消除歧义，提升 RAG 召回率，改写失败时优雅降级。"
