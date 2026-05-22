# 改动摘要：Phase 3 - LangGraph 集成 + 对话记忆

**日期**：2026-05-22
**操作人**：Claude
**任务**：引入 LangGraph 框架，实现状态图驱动的多 Agent 路由和对话记忆

---

## 问题背景

Phase 2 使用 if-else 路由，存在以下问题：
1. 无法原生支持对话记忆（需要自己管理 messages）
2. 无法原生支持 HITL 人工介入（Phase 5 需要 LangGraph interrupt）
3. 状态图不可视，不好维护

引入 LangGraph 后，状态图驱动整个流程，记忆和 HITL 都有原生支持。

---

## 改动文件列表

### 新增文件

| 文件 | 说明 |
|---|---|
| `app/graph/state.py` | LangGraph State 定义 |
| `app/graph/nodes.py` | 状态图节点函数（6 个节点 + 1 个路由函数） |
| `app/graph/builder.py` | 状态图构建和编译 |

### 修改文件

| 文件 | 说明 |
|---|---|
| `app/agents/base.py` | Agent 支持 messages 参数，实现多轮对话记忆 |
| `web/app.py` | 从 router.py 迁移到 LangGraph，兼容 Gradio 5.x/6.x |

---

## 设计决策

### 状态图结构

```
start → classifier_node →
  ├── greeting_node → END
  ├── unknown_node → END
  ├── product_agent_node → END
  ├── fault_agent_node → END
  └── training_agent_node → END
```

5 个终端节点，每个 Agent 独立，方便后续扩展不同逻辑。

### 为什么 Agent 作为独立节点？

虽然当前三个 Agent 逻辑相同（只是 Prompt 不同），但作为独立节点的好处：
1. 后续可以给不同 Agent 加不同的检索策略
2. 后续可以给不同 Agent 加不同的后处理逻辑
3. 状态图更清晰，面试时能展示架构设计

### 对话记忆方案

- 使用 Gradio history + LangGraph State messages
- Agent 的 `run()` 方法接收 messages 参数，拼接到 LLM 输入
- 截取最近 10 条消息（MAX_HISTORY_LENGTH = 10），避免 token 溢出
- 初期不做 SQLite 持久化，够用

---

## 改动详情

### app/graph/state.py（新增）

定义 LangGraph 共享状态：

```python
class State(TypedDict):
    messages: Annotated[list, add_messages]  # 对话历史
    intent: str          # 意图类型
    confidence: float    # 置信度
    role_name: str       # Agent 身份名称
    answer: str          # 生成的回答
    sources: list        # 参考来源
    hitl_required: bool  # 预留 Phase 5
```

### app/graph/nodes.py（新增）

6 个节点函数 + 1 个路由函数：

| 节点 | 职责 |
|------|------|
| classifier_node | 意图分类，greeting/unknown 直接设 answer |
| greeting_node | 返回打招呼的友好回复 |
| unknown_node | 返回无关问题的通用回复 |
| product_agent_node | 调用产品知识 Agent |
| fault_agent_node | 调用故障排查 Agent |
| training_agent_node | 调用培训资料 Agent |
| route_by_intent | 条件边函数，根据 intent 路由 |

兼容 LangChain HumanMessage 对象和字典格式。

### app/graph/builder.py（新增）

构建 LangGraph 状态图：
- 添加 6 个节点
- 条件边从 classifier 路由到 5 个终端节点
- 全局单例模式，避免重复构建

### app/agents/base.py（修改）

- `run()` 新增 `messages: list = None` 参数
- 新增 `_build_messages()` 方法，拼接对话历史
- 截取最近 10 条消息，避免 token 溢出
- 兼容 LangChain 消息对象和字典格式

### web/app.py（修改）

- 从 `router.route()` 迁移到 `graph.invoke()`
- 新增 `_convert_history()` 函数，兼容 Gradio 5.x/6.x
- Gradio 6.x history 格式从 `[["user", "assistant"], ...]` 变为 `[{"role": "user", "content": "..."}, ...]`

---

## 测试验证

| 测试场景 | 预期结果 |
|---|---|
| "你好" | greeting (0.95)，友好回复 |
| "如何搭建实验环境？" | training (0.90)，培训顾问回答 |
| "这个箱子有什么功能？" | product (0.95)，产品专家回答 |
| "传感器不亮了" | fault (0.90)，技术支持分步排查 |
| "今天天气怎么样？" | unknown (0.30)，通用回复 |
| 多轮对话 | 历史传递成功，第二轮能理解上下文 |

---

## 面试亮点

1. **LangGraph 状态图**：用状态图驱动多 Agent 路由，比 if-else 更可维护
2. **对话记忆**：通过 State messages 实现多轮对话，截断策略避免 token 溢出
3. **可扩展架构**：5 个独立节点，后续加查询重写、HITL 等节点不用改图结构
4. **兼容性处理**：同时兼容 Gradio 5.x/6.x 和 LangChain 消息对象
