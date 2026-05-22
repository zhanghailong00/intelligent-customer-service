# 改动摘要：Phase 2 - 意图分类与多 Agent 架构

**日期**：2026-05-22
**操作人**：Claude
**任务**：实现基于 LLM 的意图分类和多 Agent 路由架构

---

## 改动文件列表

### 新增文件

| 文件 | 说明 |
|---|---|
| `app/llm/intent_classifier.py` | 意图分类模块 |
| `app/agents/base.py` | Agent 基类 |
| `app/agents/product.py` | 产品知识 Agent |
| `app/agents/fault.py` | 故障排查 Agent |
| `app/agents/training.py` | 培训资料 Agent |
| `app/graph/router.py` | 路由器（意图分类 → Agent 分发） |
| `changelogs/2026-05-22_phase2_step1_intent_and_agents.md` | 本改动摘要 |

---

## 设计决策

### 为什么用 LLM 意图分类而不是关键词规则？

| 方式 | 优点 | 缺点 |
|------|------|------|
| 关键词规则 | 快、便宜 | 覆盖不全，维护成本高 |
| **LLM 意图分类（采用）** | 灵活、准确 | 多一次 API 调用（可接受） |

LLM 能理解模糊表达，比如"箱子坏了"也能正确分类为故障排查。

### 为什么共享知识库而不是多个 collection？

简单、不需要维护多个向量数据库。三个 Agent 用同一个 ChromaDB，靠不同的 System Prompt 区分角色。

### 为什么不用 LangGraph？

当前路由逻辑是 if-else，不需要复杂状态图。Phase 5 需要人工审核（HITL）时再引入 LangGraph。

---

## 每个文件的改动详情

### app/llm/intent_classifier.py（新增）

**功能**：使用 LLM 对用户问题进行意图分类

**三种意图**：
- `product`（产品咨询）：功能、参数、使用方法
- `fault`（故障排查）：设备故障、报错、异常
- `training`（培训指导）：教学资料、实验指导、课件

**关键设计**：
- 通用分类 Prompt，不硬编码关键词
- 输出结构化 JSON：`{"intent": "xxx", "confidence": 0.95}`
- 置信度阈值 0.6，低于此值降级为 unknown
- temperature=0.1，结果更确定

### app/agents/base.py（新增）

**功能**：Agent 基类，定义统一接口

**核心逻辑**：检索 → 构建上下文 → LLM 生成

**设计亮点**：
- 子类只需覆写 `system_prompt`，其他逻辑复用
- 共享 RAG 检索（同一个 ChromaDB）
- 共享 LLM 调用（支持 Fallback）

### app/agents/product.py / fault.py / training.py（新增）

每个 Agent 只有不同的 System Prompt：

| Agent | 角色定位 | 回答风格 |
|-------|---------|---------|
| ProductAgent | 产品专家 | 参数、规格、使用说明 |
| FaultAgent | 技术支持工程师 | 诊断步骤、解决方案 |
| TrainingAgent | 培训顾问 | 实验指导、教学大纲 |

### app/graph/router.py（新增）

**功能**：意图分类 → Agent 分发

**流程**：
```
用户提问 → classify_intent() → 选择 Agent → agent.run()
```

**兜底逻辑**：未知意图时使用产品 Agent（最通用）

---

## 测试验证

| 测试场景 | 预期结果 |
|---|---|
| "这个箱子有什么功能？" | product Agent 回答 |
| "传感器不亮了" | fault Agent 回答 |
| "有课件吗？" | training Agent 回答 |
| "今天天气怎么样？" | product Agent 兜底 |

---

## 面试亮点

1. **LLM 意图分类**：比关键词规则灵活，能处理模糊表达
2. **Agent 架构**：基类 + 子类，易于扩展新 Agent
3. **共享知识库**：简单高效，避免维护多个向量数据库
4. **渐进式架构**：先 if-else 路由，Phase 5 再引入 LangGraph
