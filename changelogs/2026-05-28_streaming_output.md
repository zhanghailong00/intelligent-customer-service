# 改动摘要：流式输出（伪流式）

**日期**：2026-05-28
**操作人**：Claude
**任务**：Gradio 界面支持流式输出，提升用户体验

---

## 改动文件列表

### 修改文件

| 文件 | 说明 |
|---|---|
| `app/llm/models.py` | 添加 `chat_stream()` 流式函数（备用，后续真流式使用） |
| `web/app.py` | `chat()` 改为生成器函数，支持逐 token 输出 |

---

## 设计决策

### 为什么是伪流式？

当前采用"伪流式"方案：LangGraph 同步处理完成后，逐字符显示回答。

```
用户提问 → LangGraph 同步处理（3-5秒）→ 获取完整回答 → 逐字符显示
```

**原因**：
1. LangGraph 内部的 Agent 调用 `chat()` 是同步的，返回完整回答
2. 要实现真流式需要修改 Agent 基类，改动较大
3. 伪流式已经能改善用户感知（看到逐字显示效果）

### 真流式 vs 伪流式

| 方面 | 伪流式（当前） | 真流式（后续优化） |
|------|--------------|------------------|
| 首字延迟 | 3-5秒 | <1秒 |
| 总耗时 | 3-5秒 + 显示时间 | 3-5秒 |
| 用户感知 | 等待后快速显示 | 立即开始显示 |
| 实现复杂度 | 低 | 高 |

### 流式输出配置

```python
# web/app.py
STREAM_DELAY = 0.02  # 每个 token 的延迟（秒），控制打字速度
```

- 0.02 秒/字符 = 50 字符/秒
- 可根据实际效果调整

---

## 代码实现

### _stream_response() 函数

```python
def _stream_response(text: str):
    """
    将文本逐 token 输出（生成器函数）
    模拟打字效果，提升用户体验。
    """
    current = ""
    for char in text:
        current += char
        yield current
        time.sleep(STREAM_DELAY)
```

### chat() 函数改造

```python
def chat(message, history):
    """
    聊天函数（支持流式输出）
    改为生成器函数，使用 yield 返回结果。
    """
    # ... 处理逻辑 ...

    # 正常输出（流式显示）
    response = _format_response(result)
    yield from _stream_response(response)
```

### chat_stream() 函数（备用）

```python
# app/llm/models.py
def chat_stream(messages: list, temperature: float = 0.7) -> Generator[str, None, None]:
    """
    与 LLM 对话（流式输出）
    使用 llm.stream() 逐 token 返回。
    """
    primary_llm = get_llm(temperature, provider="primary")
    for chunk in primary_llm.stream(lc_messages):
        if chunk.content:
            yield chunk.content
```

---

## 测试验证

| 测试场景 | 预期效果 |
|----------|---------|
| 正常问答 | 回答逐字显示，像打字一样 |
| HITL 触发 | 快照信息逐字显示 |
| 人工回复 | 直接显示，不逐字 |
| 错误处理 | 错误信息逐字显示 |

---

## 后续优化

**真流式输出**（待实现）：
1. 修改 Agent 基类，让 `run()` 支持流式返回
2. 修改 Gradio 界面，接收流式 token
3. 注意 LangGraph State 管理的兼容性

**相关文件**：
- `app/llm/models.py`：已有 `chat_stream()` 函数
- `app/agents/base.py`：需要支持流式
- `web/app.py`：需要处理流式输入

---

## 面试亮点

1. **流式输出设计**：理解伪流式和真流式的区别，选择合适的方案
2. **用户体验优化**：逐字显示提升用户感知，即使后端处理时间不变
3. **渐进式优化**：先实现伪流式验证效果，后续再优化为真流式
4. **技术债务管理**：记录待优化项，规划后续改进
