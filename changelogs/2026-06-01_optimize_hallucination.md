# 改动摘要：优化回答编撰问题

**日期**：2026-06-01
**操作人**：Claude
**任务**：优化 LLM 回答编撰问题，提高回答准确性

---

## 问题描述

用户反馈智能客服的回答存在编撰痕迹，LLM 在没有参考资料时仍会编造内容。

**原因分析**：
1. Temperature 太高（0.7），LLM 生成更自由，容易编造
2. Prompt 拒绝策略不够强，LLM 没有严格遵循
3. 检索结果为空时仍调用 LLM，LLM 可能编造

---

## 改动文件列表

### 修改文件

| 文件 | 说明 |
|------|------|
| `app/llm/models.py` | 降低 Temperature 默认值，从 0.7 改为 0.3 |
| `app/agents/base.py` | 检索结果为空时，直接返回拒绝回答，不调用 LLM |
| `app/agents/product.py` | 优化 Prompt，更强调拒绝策略 |
| `app/agents/fault.py` | 优化 Prompt，更强调拒绝策略 |
| `app/agents/training.py` | 优化 Prompt，更强调拒绝策略 |

---

## 优化方案

### 1. 降低 Temperature

**文件**：`app/llm/models.py`

**修改内容**：
- `chat()` 函数：`temperature: float = 0.7` → `temperature: float = 0.3`
- `chat_stream()` 函数：`temperature: float = 0.7` → `temperature: float = 0.3`
- `chat_with_fallback_status()` 函数：`temperature: float = 0.7` → `temperature: float = 0.3`

**原理**：Temperature 越低，LLM 生成越确定，越不容易编造。

---

### 2. 优化 Prompt 拒绝策略

**文件**：`app/agents/product.py`、`app/agents/fault.py`、`app/agents/training.py`

**修改内容**：

**修改前**：
```python
## 回答原则
1. **基于资料**：只使用参考资料中的信息回答，不编造任何产品参数或功能
2. **拒绝策略**：如果参考资料中没有相关信息，明确告知"目前我没有找到相关产品资料，建议您联系技术支持确认"
```

**修改后**：
```python
## 回答原则（严格执行）
1. **基于资料**：只使用参考资料中的信息回答，**严禁编造任何内容**
2. **拒绝策略**：如果参考资料中没有相关信息，**必须**明确告知"目前我没有找到相关产品资料，建议您联系技术支持确认"
3. **不确定时拒绝**：如果不确定，**必须**拒绝回答，不要猜测
4. **引用来源**：回答时引用参考资料的编号，如"根据文档1..."
```

**原理**：更强调拒绝策略，让 LLM 更严格遵循。

---

### 3. 检索为空时跳过 LLM

**文件**：`app/agents/base.py`

**修改内容**：

**修改前**：
```python
def run(self, user_query: str, messages: list = None, top_k: int = 3) -> Dict[str, any]:
    # 1. 查询改写
    rewritten_query = rewrite_query(user_query, self.role_name, messages)

    # 2. 两步检索
    retrieval_results = self._two_step_retrieve(user_query, rewritten_query, top_k)

    # 3. 构建上下文
    context = self._build_context(retrieval_results)

    # 4. 调用 LLM 生成回答
    answer = chat(llm_messages)
    ...
```

**修改后**：
```python
def run(self, user_query: str, messages: list = None, top_k: int = 3) -> Dict[str, any]:
    # 1. 查询改写
    rewritten_query = rewrite_query(user_query, self.role_name, messages)

    # 2. 两步检索
    retrieval_results = self._two_step_retrieve(user_query, rewritten_query, top_k)

    # 3. 如果检索结果为空，直接返回拒绝回答，不调用 LLM
    if not retrieval_results:
        print(f"[Agent] 检索结果为空，直接返回拒绝回答")
        return {
            "answer": f"目前我没有找到相关{self.role_name}资料，建议您联系技术支持确认。",
            "sources": [],
            "intent": self.name
        }

    # 4. 构建上下文
    context = self._build_context(retrieval_results)

    # 5. 调用 LLM 生成回答
    answer = chat(llm_messages)
    ...
```

**原理**：检索结果为空时，直接返回拒绝回答，不调用 LLM，彻底解决编撰问题。

---

## 测试验证

| 测试场景 | 预期结果 | 实际结果 |
|----------|---------|---------|
| 问题："这个箱子支持5G吗？"（检索为空） | 返回"目前我没有找到相关产品资料，建议您联系技术支持确认。" | ✅ |
| 问题："传感器不亮了怎么办？"（检索有内容） | 基于参考资料回答，不编造 | ✅ |
| 问题："怎么做人工智能实验？"（检索为空） | 返回"目前我没有找到相关培训顾问资料，建议您联系技术支持确认。" | ✅ |

---

## 优化效果

| 优化项 | 效果 |
|--------|------|
| **降低 Temperature** | LLM 生成更确定，减少编造 |
| **优化 Prompt** | LLM 更严格遵循拒绝策略 |
| **检索为空跳过 LLM** | 彻底解决检索为空时的编撰问题 |

---

## 后续优化

1. **后处理检查**：检测回答是否包含编造内容（可选）
2. **知识库扩充**：增加更多实验手册，提高检索命中率
3. **图文混排**：回答中包含文档图片，提升用户体验
