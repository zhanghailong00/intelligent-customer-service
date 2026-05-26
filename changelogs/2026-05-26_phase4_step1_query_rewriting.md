# 改动摘要：Phase 4 Step 1 - Query Rewriting 查询改写（v2）

**日期**：2026-05-26
**操作人**：Claude
**任务**：Phase 4 查询优化 — 历史感知改写 + 两步检索 + 降级机制

---

## 改动文件列表

### 新增文件

| 文件 | 说明 |
|---|---|
| `app/query/__init__.py` | query 模块初始化 |
| `app/query/rewriter.py` | 查询改写模块（历史感知 + LLM 改写 + 降级机制） |

### 修改文件

| 文件 | 说明 |
|---|---|
| `app/agents/base.py` | Agent.run() 支持历史感知改写 + 两步检索 + 合并去重 |

---

## 功能特性

### 1. 历史对话上下文感知

**问题**：多轮对话中，后续问题常省略主语或用代词（"怎么修"、"那个报错"），改写时缺少上下文。

**解决方案**：将最近 3 轮对话历史传入改写 prompt，让 LLM 理解上下文。

```
历史：用户问"传感器不亮了"
当前："怎么修" → "传感器不亮了怎么维修"  ✅ 正确理解上下文
```

**历史格式化**：
- 支持 LangChain 消息对象（HumanMessage/AIMessage）
- 支持字典格式（{"role": "user", "content": "..."}）
- 支持 LangChain v0.2+ 的 content 列表格式（[{"type": "text", "text": "..."}]）
- 截断过长内容（>100字符），避免 prompt 过长

### 2. 两步检索 + 合并去重

**问题**：单一 query 检索可能遗漏相关文档。

**解决方案**：用原始 query 和改写后 query 分别检索，合并去重。

```
原始 query ─────→ 检索 1 ──┐
                              ├──→ 合并去重 → top_k
改写后 query ───→ 检索 2 ──┘
```

**合并策略**：
- 按 source 字段去重（同一篇文档只保留一条）
- 保留相似度分数高的结果
- 最终返回 top_k 条

**优势**：
- 召回率更高：两种 query 覆盖不同角度
- 更鲁棒：改写失败时，原始 query 仍然有效
- 互补：原始 query 可能命中精确匹配，改写后 query 命中语义匹配

### 3. 降级机制

**问题**：LLM 调用失败时，不能影响系统稳定性。

**解决方案**：改写失败时返回原始 query。

```python
try:
    response = chat(...)  # 调用 LLM 改写
    return response.strip()
except:
    return query  # 降级：返回原始 query
```

**降级场景**：
- LLM API 超时
- LLM API 返回错误
- 改写结果为空
- 网络异常

**效果**：改写失败 → 用原始 query → 检索质量和改写前一样，不影响系统稳定性。

### 4. 作用范围设计

```
用户提问
    ↓
classifier_node（意图分类）  ← 用原始 query，不改写
    ↓
Agent 节点
    ├── rewrite_query(query, role, history)  ← 基于历史改写
    ├── retrieve(original)  ──┐
    │                         ├──→ 合并去重 → 结果
    └── retrieve(rewritten) ──┘
    ↓
hitl_checker_node（HITL 检测）← 用原始 query，不改写
```

**核心原则**：改写只用于检索，不影响意图识别和 HITL 检测。

**为什么不改写 HITL？**
- HITL 关键词匹配依赖原始表述（"转人工"不能改写为"用户想要转接人工客服"）
- 改写会增加不必要的开销

### 5. 角色感知改写

不同 Agent 有不同的改写上下文：

| Agent | 角色 | 改写方向 |
|-------|------|---------|
| ProductAgent | 产品专家 | 补充产品名称、型号、功能参数 |
| FaultAgent | 故障排查 | 补充故障现象、设备名称、错误信息 |
| TrainingAgent | 培训指导 | 补充实验名称、课程内容 |

---

## 完整流程

```
用户提问 + 历史对话
    ↓
rewrite_query(query, context, history)
    ├── 格式化历史（最近 3 轮）
    ├── 构建 prompt（角色 + 历史 + 问题）
    └── 调用 LLM 改写（失败时降级）
    ↓
┌─────────────────────────────────────┐
│  原始 query ──→ retrieve() ──┐      │
│                               ├──→ 合并去重 → top_k
│  改写后 query → retrieve() ──┘      │
└─────────────────────────────────────┘
    ↓
构建上下文 → LLM 生成回答
```

---

## 代码实现

### rewriter.py 核心代码

```python
REWRITE_PROMPT = """你是一个查询优化专家。

当前场景：{context}
对话历史：
{history}

改写要求：
1. 参考对话历史，理解当前问题的上下文
2. 如果当前问题包含代词或省略了主语，根据历史补充完整
3. 补充缺失的上下文
4. 保持原意

用户问题：{query}
改写后："""

def rewrite_query(query: str, context: str = "", history: list = None) -> str:
    # 格式化历史（支持多种消息格式）
    history_text = _format_history(history)
    # 调用 LLM 改写
    response = chat(messages=[...], temperature=0.3)
    return response.strip()

def _format_history(messages: list, max_turns: int = 3) -> str:
    # 支持 LangChain 消息对象和字典格式
    # 支持 content 为字符串或列表格式
    # 截断过长内容
    pass
```

### base.py 核心代码

```python
def run(self, user_query, messages=None, top_k=3):
    # 1. 查询改写（传入历史）
    rewritten_query = rewrite_query(user_query, self.role_name, messages)

    # 2. 两步检索 + 合并去重
    retrieval_results = self._two_step_retrieve(user_query, rewritten_query, top_k)

    # 3. 后续用原始 query
    context = self._build_context(retrieval_results)
    llm_messages = self._build_messages(user_query, context, messages)
    answer = chat(llm_messages)

def _two_step_retrieve(self, original_query, rewritten_query, top_k):
    # 原始 query 检索
    results_original = retrieve(original_query, top_k=top_k)
    # 改写后 query 检索
    results_rewritten = retrieve(rewritten_query, top_k=top_k)
    # 合并去重（按 source 去重，保留分数高的）
    merged = {}
    for r in results_original + results_rewritten:
        source = r["metadata"].get("source", "")
        if source not in merged or r.get("score", 0) > merged[source].get("score", 0):
            merged[source] = r
    return sorted(merged.values(), key=lambda x: x.get("score", 0), reverse=True)[:top_k]
```

---

## 测试验证

| 测试场景 | 原始 query | 改写后 | 检索结果 |
|----------|-----------|--------|---------|
| 完整问题 | "上传文件到实验平台" | "如何上传文件到实验平台" | 3+3→3条 |
| 同义转换 | "文件怎么放到实验平台上" | "如何将文件上传到实验平台" | 3+3→2条（去重） |
| 修正错别字 | "实验平台怎么登陆" | "实验平台怎么登录" | 3+3→3条 |
| 多轮对话 | "怎么修"（历史：传感器不亮） | "传感器不亮了怎么维修" | ✅ 召回相关文档 |
| 降级测试 | LLM 失败时 | 返回原始 query | ✅ 不影响系统 |

---

## 面试亮点

1. **历史感知改写**：基于对话历史理解多轮上下文，解决代词和省略主语问题
2. **两步检索**：原始 query + 改写后 query 分别检索，合并去重，提升召回率和鲁棒性
3. **降级机制**：改写失败时用原始 query，不影响系统稳定性
4. **作用范围设计**：改写只用于检索，不影响意图识别和 HITL 检测
5. **多格式兼容**：支持 LangChain 消息对象、字典格式、content 列表格式
6. **角色感知**：不同 Agent 有不同的改写上下文
