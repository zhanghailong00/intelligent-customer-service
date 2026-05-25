# 改动摘要：Phase 5 Step 4 - Gradio 界面适配 HITL

**日期**：2026-05-23
**操作人**：Claude
**任务**：Gradio 界面支持 HITL interrupt 暂停/恢复流程

---

## 改动文件列表

### 修改文件

| 文件 | 说明 |
|---|---|
| `app/graph/builder.py` | 添加 MemorySaver checkpointer，支持 interrupt 暂停/恢复 |
| `web/app.py` | 捕获 Interrupt 异常，显示"转人工"提示，支持恢复图执行 |

---

## 设计决策

### HITL 交互流程

```
用户提问 → Agent 回答 → hitl_checker 检测
  ├── 不需要人工 → 正常返回回答
  └── 需要人工 → interrupt() 暂停图
      ↓
      Gradio 显示"⏳ 需要人工介入"提示
      ↓
      用户输入回复（模拟人工审核）
      ↓
      Command(resume=message) 恢复图执行
      ↓
      返回最终回答
```

### 为什么用 MemorySaver 而不是 SQLite？

| 方案 | 优点 | 缺点 |
|------|------|------|
| **MemorySaver（采用）** | 零配置，开发环境够用 | 内存存储，重启丢失 |
| SQLite | 持久化 | 需要额外配置，开发期过度设计 |

开发阶段用 MemorySaver，上线时再切换到 SQLite/Redis。

### 简化的 interrupt 状态管理

使用模块级变量 `_pending_interrupt` 记录待处理的 interrupt：

```python
_pending_interrupt = None  # 全局状态

# 触发时保存
_pending_interrupt = {"config": config}

# 恢复时清除
result = graph.invoke(Command(resume=message), config=config)
_pending_interrupt = None
```

**适用场景**：单用户开发环境。生产环境需改为 per-session 状态管理。

---

## 改动详情

### app/graph/builder.py

| 改动 | 说明 |
|------|------|
| 导入 MemorySaver | `from langgraph.checkpoint.memory import MemorySaver` |
| build_graph 新增 checkpointer 参数 | 支持传入不同的 checkpointer |
| get_graph 创建 MemorySaver | 单例模式，全局共享同一个 checkpointer |

### web/app.py

| 改动 | 说明 |
|------|------|
| 导入 Interrupt 和 Command | `from langgraph.errors import Interrupt` / `from langgraph.types import Command` |
| 新增 _pending_interrupt | 模块级变量，记录待处理的 interrupt 状态 |
| chat() 捕获 Interrupt 异常 | 显示"转人工"提示，保存 config 用于恢复 |
| chat() 恢复逻辑 | 检测 _pending_interrupt，用 Command(resume=) 恢复图 |
| 新增 _format_response() | 提取格式化逻辑，避免重复代码 |
| graph.invoke() 传入 config | 包含 thread_id，支持 checkpointer 持久化状态 |

---

## 测试场景

| 场景 | 操作 | 预期结果 |
|------|------|---------|
| 正常问答 | 问"这个箱子有什么功能？" | 正常返回回答，不触发 HITL |
| 打招呼 | 说"你好" | 正常返回友好回复，不触发 HITL |
| 触发转人工 | 问"转人工" | 显示"⏳ 需要人工介入"提示 |
| 恢复 HITL | 在提示后输入回复 | 返回人工回复，图执行完成 |
| Agent 拒绝 | （需要 Agent 实际拒绝才触发） | 显示转人工提示 |

---

## 面试亮点

1. **LangGraph interrupt 机制**：图执行暂停/恢复，天然支持 HITL
2. **MemorySaver checkpointer**：状态持久化，支持图的暂停和恢复
3. **Command(resume)**：LangGraph 恢复图执行的标准方式
4. **优雅降级**：interrupt 触发时显示友好提示，而不是报错
