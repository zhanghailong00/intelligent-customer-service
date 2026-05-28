# 改动摘要：Phase 5 Step 1-2 - HITL 检测逻辑和节点

**日期**：2026-05-25
**操作人**：Claude
**任务**：实现 HITL（Human-in-the-Loop）检测逻辑和节点

---

## 改动文件列表

### 新增文件

| 文件 | 说明 |
|---|---|
| `app/hitl/detector.py` | HITL 检测逻辑（3 个必做检测 + 1 个可选检测） |

### 修改文件

| 文件 | 说明 |
|---|---|
| `app/graph/nodes.py` | 新增 hitl_checker_node，导入 detector 模块 |

---

## 设计决策

### 为什么 HITL 作为独立节点而不是嵌入 Agent？

| 方案 | 优点 | 缺点 |
|------|------|------|
| **独立节点（采用）** | 逻辑集中，改一处就行 | 多一个节点 |
| 嵌入 Agent 节点 | 不加新节点 | 三个 Agent 都要重复写 HITL 逻辑 |

### 为什么不在 Agent 内部决定转人工？

HITL 是系统的兜底机制，不是 Agent 的选择。应该在 Agent 执行完后由系统判断，不该让 Agent 自己决定"我搞不定，转人工吧"。

---

## 改动详情

### app/hitl/detector.py（新增）

**关键词库**：
- `REFUSAL_KEYWORDS`：Agent 拒绝关键词（"我不确定"/"建议联系技术支持"等）
- `HUMAN_REQUEST_KEYWORDS`：用户主动要求转人工（"转人工"/"找客服"等）
- `SENSITIVE_KEYWORDS`：敏感问题（"退款"/"投诉"/"法律"等，可选）

**检测函数**：
| 函数 | 检测内容 |
|------|---------|
| `check_agent_refusal()` | Agent 回复是否包含拒绝关键词 |
| `check_user_request_human()` | 用户是否主动要求转人工 |
| `check_low_confidence()` | 置信度是否低于阈值 |
| `check_sensitive_content()` | 是否包含敏感内容（可选） |

**核心函数**：`should_escalate_to_human()` 综合判断是否需要转人工

### app/graph/nodes.py（修改）

**新增 hitl_checker_node**：
- 获取 Agent 的回答、对话历史、置信度
- 调用 `should_escalate_to_human()` 综合判断
- 需要人工时调用 `interrupt()` 暂停图执行
- 不需要人工时继续到 END

---

## 测试验证

| 测试场景 | 预期结果 |
|---|---|
| Agent 回复包含"我不确定" | 触发转人工 |
| 用户说"转人工" | 触发转人工 |
| 置信度 < 0.5 | 触发转人工 |
| 正常回答 | 不触发 |

---

## 面试亮点

1. **LangGraph interrupt 机制**：图执行暂停/恢复，天然支持 HITL
2. **多维度检测**：Agent 拒绝 + 用户要求 + 置信度低，三重保障
3. **可扩展设计**：敏感问题、情绪分析等可选检测预留接口
