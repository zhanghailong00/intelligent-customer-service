# 改动摘要：Phase 5 Step 3 - 状态图连接 HITL 节点

**日期**：2026-05-23
**操作人**：Claude
**任务**：修改 builder.py，将 Agent 节点连接到 hitl_checker_node

---

## 改动文件列表

### 修改文件

| 文件 | 说明 |
|---|---|
| `app/graph/builder.py` | 新增 hitl_checker_node，Agent 出口从 END 改为 hitl_checker_node |

---

## 状态图变化

### 修改前

```
start → classifier_node →
  ├── greeting_node → END
  ├── unknown_node → END
  ├── product_agent_node → END
  ├── fault_agent_node → END
  └── training_agent_node → END
```

### 修改后

```
start → classifier_node →
  ├── greeting_node → END
  ├── unknown_node → END
  ├── product_agent_node → hitl_checker_node → END
  ├── fault_agent_node   → hitl_checker_node → END
  └── training_agent_node → hitl_checker_node → END
```

---

## 设计决策

### 为什么 greeting/unknown 不经过 HITL？

| 节点 | 是否需要 HITL | 原因 |
|---|---|---|
| greeting_node | 否 | 固定回复，不存在"答不上来"的场景 |
| unknown_node | 否 | 固定回复，已明确告知用户问题不在服务范围 |
| product_agent_node | 是 | Agent 可能检索不到相关内容，需要转人工 |
| fault_agent_node | 是 | 故障排查可能无法解决，需要人工远程协助 |
| training_agent_node | 是 | 培训资料可能不完整，需要人工补充 |

### HITL 检测逻辑回顾

hitl_checker_node 在 Agent 执行完后触发，执行三个必做检测：
1. **Agent 拒绝检测**：回复是否包含"我不确定"等拒绝关键词
2. **用户主动要求检测**：用户是否说了"转人工"
3. **置信度检测**：confidence < 0.5 时触发

---

## 已知限制

### interrupt() 需要 checkpointer

`langgraph.types.interrupt()` 必须配合 checkpointer 使用，否则会报错。当前 `web/app.py` 的 `graph.invoke()` 没有传入 checkpointer。

**解决方案**：Step 4 适配 Gradio 时，在 `get_graph()` 中传入 `MemorySaver` 作为 checkpointer。

---

## 面试亮点

1. **条件路由设计**：greeting/unknown 跳过 HITL，避免不必要的检测开销
2. **统一出口**：三个 Agent 共享同一个 hitl_checker_node，避免重复代码
3. **图结构清晰**：状态图可视化后，一目了然的数据流向
