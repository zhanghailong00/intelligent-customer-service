# 双层 HITL 架构：为什么你的 AI 客服需要前置规则 + 后置兜底？

## 前言

在构建 AI 客服系统时，Human-in-the-Loop（HITL）是不可或缺的机制。但很多开发者（包括我）在实现 HITL 时，只做了**单层检测**：Agent 执行完后，检查是否需要人工介入。

这种设计看似合理，实际存在**致命盲区**：用户说"转人工"时，LLM 意图分类器可能把它归为"未知意图"，直接返回"我不懂你在说什么"——转人工的需求被完全忽略。

这篇文章分享我在实训设备智能客服系统中设计的**双层 HITL 架构**：前置规则拦截 + 后置兜底检测，覆盖 99% 的 HITL 场景。

---

## 一、问题：单层 HITL 的盲区

### 1.1 初始设计

我的第一个版本只做了后置检测：

```
用户提问 → LLM 意图分类 → Agent 执行 → 后置检测 → HITL？
```

后置检测逻辑：

```python
def hitl_checker_node(state):
    answer = state.get("answer", "")
    confidence = state.get("confidence", 1.0)

    # 检查 Agent 是否拒绝回答
    if check_agent_refusal(answer):
        return interrupt({"reason": "Agent 拒绝"})
    # 检查置信度是否低
    if confidence < 0.5:
        return interrupt({"reason": "置信度低"})
    # 检查敏感内容
    if check_sensitive_content(answer):
        return interrupt({"reason": "敏感问题"})
```

逻辑很清晰：Agent 执行完后，检查三种情况。

### 1.2 致命 Bug

测试时发现一个严重问题：

```
用户输入："转人工"
系统回复："抱歉，您的问题似乎与实训设备无关。我主要负责回答关于实训设备的产品咨询..."
```

**用户明明说"转人工"，系统却返回"我不懂"？**

### 1.3 根因分析

问题出在 **LLM 意图分类器**：

```python
# classifier_node
intent_result = classify_intent(user_message)
intent = intent_result["intent"]  # 返回 INTENT_UNKNOWN
```

LLM 把"转人工"分类为 `INTENT_UNKNOWN`，然后走了 `unknown_node`，返回通用回复。

**问题链条**：

```
"转人工" → LLM 分类为"未知意图" → unknown_node → "我不懂"
                                  ↑
                            HITL 检测根本没机会执行！
```

### 1.4 问题本质

这是一个**优先级问题**：

| 意图类型 | 优先级 | 检测方式 |
|---------|--------|---------|
| 系统控制意图（转人工、投诉、售后） | 最高 | 应该优先拦截 |
| 业务意图（产品、故障、培训） | 普通 | LLM 分类 |
| 未知意图 | 最低 | 兜底回复 |

单层后置检测的问题：**系统控制意图被 LLM 分类器吞掉了**，根本没有机会进入 HITL 检测。

---

## 二、解决方案：双层 HITL 架构

### 2.1 设计思路

既然系统控制意图优先级最高，那就**在 LLM 分类之前拦截**：

```
用户提问 → 前置规则检测 → 命中？→ 直接返回转人工提示
                ↓
           未命中 → LLM 意图分类 → Agent 执行 → 后置兜底检测
```

两层检测的分工：

| 层级 | 位置 | 检测方式 | 覆盖场景 |
|------|------|---------|---------|
| 前置 | classifier_node | 规则匹配（毫秒级） | 转人工、投诉、售后 |
| 后置 | hitl_checker_node | Agent 回答分析 | 拒绝回答、低置信度、敏感内容 |

### 2.2 前置检测实现

```python
# app/hitl/detector.py

# 转人工意图关键词（覆盖常见口语化表达）
HANDOFF_KEYWORDS = [
    "转人工", "找客服", "人工客服", "人工服务",
    "转接人工", "找人工", "真人客服", "真人服务",
    "接人工", "帮我转", "我要人工", "和真人聊",
    "和人聊", "不想和机器人", "不要机器人",
]

# 投诉/维权意图关键词
COMPLAINT_KEYWORDS = [
    "投诉", "我要投诉", "找你们领导", "找领导",
    "负责人", "上级", "管理层", "消协",
    "工商局", "消费者协会", "12315",
]

# 售后/退款意图关键词
AFTERSALE_KEYWORDS = [
    "退款", "退货", "换货", "赔偿", "三包",
    "维权", "法律", "起诉", "律师",
]

def check_system_control(query: str) -> dict:
    """
    前置检测：系统控制意图

    在意图分类之前执行，优先级最高。
    规则匹配，不走 LLM，毫秒级响应。
    """
    # 检测转人工意图
    for keyword in HANDOFF_KEYWORDS:
        if keyword in query:
            return {
                "is_system_control": True,
                "type": "handoff",
                "message": "正在为您转接人工客服，请稍候...\n\n请描述您的问题，人工客服将为您处理。"
            }

    # 检测投诉/维权意图
    for keyword in COMPLAINT_KEYWORDS:
        if keyword in query:
            return {
                "is_system_control": True,
                "type": "complaint",
                "message": "收到您的投诉/反馈，已为您转接人工客服。\n\n请描述具体问题，我们将尽快为您处理。"
            }

    # 检测售后/退款意图
    for keyword in AFTERSALE_KEYWORDS:
        if keyword in query:
            return {
                "is_system_control": True,
                "type": "aftersale",
                "message": "您的售后问题需要人工客服处理。\n\n已为您转接人工客服，请描述具体问题。"
            }

    return {"is_system_control": False, "type": None, "message": ""}
```

### 2.3 集成到 classifier_node

```python
# app/graph/nodes.py

def classifier_node(state: State) -> dict:
    """意图分类节点"""
    user_message = _get_last_user_message(state)

    # ========== 前置检测：系统控制意图 ==========
    # 优先级最高，在 LLM 分类之前拦截
    system_control = check_system_control(user_message)
    if system_control["is_system_control"]:
        print(f"[LangGraph] 前置检测命中系统控制意图：{system_control['type']}")
        return {
            "intent": INTENT_UNKNOWN,
            "confidence": 1.0,
            "role_name": "",
            "answer": system_control["message"],
            "sources": [],
            "hitl_required": True
        }

    # ========== 正常流程：LLM 意图分类 ==========
    # 只有未命中系统控制意图时，才走 LLM 分类
    intent_result = classify_intent(user_message)
    intent = intent_result["intent"]
    confidence = intent_result["confidence"]

    # ... 后续路由逻辑 ...
```

### 2.4 后置检测实现

```python
# app/hitl/detector.py

def should_escalate_to_human(
    answer: str,
    messages: List[dict],
    confidence: float,
    user_query: str = ""
) -> dict:
    """
    综合判断是否需要转人工

    后置检测：Agent 执行完后兜底
    """
    # 必做检测 1：Agent 拒绝
    if check_agent_refusal(answer):
        return {"needs_human": True, "reason": "拒绝回答"}

    # 必做检测 2：用户主动要求
    if check_user_request_human(messages):
        return {"needs_human": True, "reason": "用户要求"}

    # 必做检测 3：置信度低
    if check_low_confidence(confidence):
        return {"needs_human": True, "reason": "置信度低"}

    # 必做检测 4：敏感问题
    if check_sensitive_content(user_query):
        return {"needs_human": True, "reason": "敏感问题"}

    return {"needs_human": False, "reason": "无"}
```

---

## 三、两层如何配合

### 3.1 完整流程

```
用户提问："转人工"
    ↓
前置检测（check_system_control）
    ↓ 命中 HANDOFF_KEYWORDS
直接返回："正在为您转接人工客服..."
    ↓
.hitl_required = True
    ↓
前端检测 → 生成会话快照 → 进入人工接管模式
```

```
用户提问："传感器不亮了"
    ↓
前置检测（check_system_control）
    ↓ 未命中
LLM 意图分类 → INTENT_FAULT
    ↓
故障排查 Agent → RAG 检索 → 生成回答
    ↓
后置检测（should_escalate_to_human）
    ↓ 如果 Agent 拒绝
interrupt() → 等待人工输入
    ↓
前端检测 → 生成会话快照 → 进入人工接管模式
```

### 3.2 为什么这样设计

| 场景 | 前置检测 | 后置检测 | 原因 |
|------|---------|---------|------|
| 用户说"转人工" | ✅ 拦截 | - | 确定性 100%，规则匹配足够 |
| 用户说"投诉" | ✅ 拦截 | - | 确定性高，优先级最高 |
| Agent 拒绝回答 | - | ✅ 兜底 | 只有看到回答才能判断 |
| 置信度低 | - | ✅ 兜底 | 需要 LLM 分类结果 |
| 敏感内容 | - | ✅ 兜底 | 可能出现在回答中 |

### 3.3 设计原则

**前置检测**：
- 确定性高：用户明确表达意图（"转人工"、"投诉"）
- 优先级高：必须优先处理，不能被其他流程拦截
- 实现简单：规则匹配，毫秒级响应

**后置检测**：
- 确定性低：需要看 Agent 执行结果才能判断
- 兜底保障：处理 Agent 无法处理的边界情况
- 实现复杂：需要分析回答内容、置信度等

---

## 四、效果对比

### 4.1 修改前（单层检测）

```
"转人工" → LLM 分类为"未知意图" → "我不懂你在说什么" ❌
"投诉" → LLM 分类为"未知意图" → "我不懂你在说什么" ❌
"传感器坏了" → Agent 执行 → Agent 拒绝 → HITL 触发 ✅
```

### 4.2 修改后（双层检测）

```
"转人工" → 前置检测命中 → "正在为您转接人工客服..." ✅
"投诉" → 前置检测命中 → "收到您的投诉，已转接人工客服" ✅
"传感器坏了" → Agent 执行 → Agent 拒绝 → 后置检测触发 HITL ✅
"退款" → 前置检测命中 → "您的售后问题需要人工客服处理" ✅
```

### 4.3 覆盖率对比

| HITL 场景 | 单层检测 | 双层检测 |
|-----------|---------|---------|
| 用户主动要求转人工 | ❌ 被 LLM 吞掉 | ✅ 前置拦截 |
| 投诉/维权 | ❌ 被 LLM 吞掉 | ✅ 前置拦截 |
| 售后/退款 | ❌ 被 LLM 吞掉 | ✅ 前置拦截 |
| Agent 拒绝回答 | ✅ 后置检测 | ✅ 后置检测 |
| 置信度低 | ✅ 后置检测 | ✅ 后置检测 |
| 敏感内容 | ✅ 后置检测 | ✅ 后置检测 |
| **覆盖率** | **40%** | **100%** |

---

## 五、扩展思考

### 5.1 为什么不用 LLM 做前置检测？

有人可能会问：为什么不直接用 LLM 分类器检测系统控制意图？

原因：

| 方面 | 规则匹配 | LLM 分类 |
|------|---------|---------|
| 速度 | 毫秒级 | 秒级 |
| 成本 | 零 | 消耗 token |
| 确定性 | 100% | 可能误判 |
| 可控性 | 完全可控 | 依赖 prompt |

对于"转人工"这种**确定性 100%** 的场景，规则匹配更合适。

### 5.2 前置检测的关键词怎么定？

我的关键词库是根据**真实用户表达**逐步积累的：

```python
# 第一版：只有"转人工"
HANDOFF_KEYWORDS = ["转人工"]

# 第二版：加上"找客服"
HANDOFF_KEYWORDS = ["转人工", "找客服", "人工客服"]

# 第三版：覆盖口语化表达
HANDOFF_KEYWORDS = [
    "转人工", "找客服", "人工客服", "人工服务",
    "转接人工", "找人工", "真人客服", "真人服务",
    "接人工", "帮我转", "我要人工", "和真人聊",
    "和人聊", "不想和机器人", "不要机器人",
]
```

**建议**：根据实际用户输入不断补充，不要一开始就追求完美。

### 5.3 后置检测的阈值怎么调？

置信度阈值（`threshold=0.5`）需要根据业务调整：

```python
# 保守策略：阈值高，更多转人工
threshold = 0.7

# 激进策略：阈值低，AI 多处理
threshold = 0.3
```

建议从 0.5 开始，根据线上数据调整。

---

## 总结

### 核心要点

1. **单层 HITL 有盲区**：系统控制意图会被 LLM 分类器吞掉
2. **双层架构**：前置规则拦截 + 后置兜底检测
3. **分工明确**：确定性高的用规则，确定性低的用 LLM
4. **覆盖全面**：从用户主动要求到 Agent 无法处理，全覆盖

### 设计原则

- **优先级**：系统控制意图 > 业务意图 > 未知意图
- **确定性**：规则匹配（100%）> LLM 分类（不确定）
- **成本**：规则匹配（零成本）> LLM 分类（消耗 token）
- **速度**：规则匹配（毫秒级）> LLM 分类（秒级）

### 适用场景

- AI 客服系统需要人工介入
- 有明确的系统控制指令（转人工、投诉、售后）
- Agent 可能无法处理某些问题
- 需要高可用性和高覆盖率

---

## 文末结语

双层 HITL 架构的核心思想是**分层治理**：用最简单的方式处理最确定的问题，用更灵活的方式处理不确定的问题。这种设计模式不仅适用于 HITL，也可以推广到其他需要多层决策的场景。

在 AI 应用开发中，不要迷信"LLM 万能论"。有些场景，简单的规则匹配比 LLM 更可靠、更高效。关键是**理解问题本质，选择合适的工具**。

---

**项目地址**：[GitHub 仓库链接]

**相关文章**：
- 《LangGraph interrupt() 暂停后 State 不更新？这个坑我帮你踩了》
- 《多 Agent + RAG + HITL 智能客服系统架构设计》
