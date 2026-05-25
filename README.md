# 智科云联 - 实训设备智能客服系统

面向高校实训设备（嵌入式实验箱）的智能客服平台，基于 **多 Agent + RAG + HITL** 架构实现产品知识问答、故障排查、培训指导等功能。

---

## 项目当前状态

**Phase 5（HITL 人工介入）已完成** - 2026-05-25

已完成的功能：
- ✅ PDF 文档自动解析和向量化存储
- ✅ 语义检索和 RAG 问答
- ✅ LLM 主备模型自动切换（DeepSeek + 通义千问）
- ✅ 多 Agent 协作（产品、故障、培训 Agent）
- ✅ LangGraph 状态图路由
- ✅ LLM 意图分类器
- ✅ HITL 双层检测（前置规则 + 后置兜底）
- ✅ 会话快照生成（LLM 提取核心诉求 + 建议方案）
- ✅ 人工接管模式（说「关闭」恢复 AI）

**下一步工作**：Phase 4 - 查询优化（Query Rewriting）

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填写以下 API Key：

```
DEEPSEEK_API_KEY=你的DeepSeek密钥
QWEN_API_KEY=你的通义千问密钥
MINERU_TOKEN=你的MinerU Token
```

### 3. 启动问答系统

```bash
# 启动 Gradio 界面
python web/app.py

# 访问 http://localhost:7860
```

### 4. 导入知识库

```bash
# 把 PDF 文件放到 data/raw/ 目录（支持子目录）

# 运行一键导入
python app/scripts/import_knowledge.py

# 查看导入状态
python app/scripts/import_knowledge.py --status
```

---

## 项目结构

```
intelligent-customer-service/
├── app/                          # 主应用模块
│   ├── config.py                 # 统一配置管理
│   ├── llm/
│   │   ├── models.py             # LLM 封装 + Fallback 机制
│   │   └── intent_classifier.py  # LLM 意图分类器
│   ├── rag/
│   │   ├── loader.py             # 文档加载和切分
│   │   ├── vectorstore.py        # 向量化存储（ChromaDB）
│   │   ├── retriever.py          # 向量检索
│   │   ├── qa_chain.py           # RAG 问答链
│   │   └── imported_files.py     # 导入记录管理
│   ├── agents/
│   │   ├── base.py               # Agent 基类
│   │   ├── product.py            # 产品知识 Agent
│   │   ├── fault.py              # 故障排查 Agent
│   │   └── training.py           # 培训资料 Agent
│   ├── graph/
│   │   ├── state.py              # LangGraph State 定义
│   │   ├── nodes.py              # 状态图节点函数
│   │   ├── builder.py            # 状态图构建
│   │   └── router.py             # 路由逻辑
│   ├── hitl/
│   │   ├── detector.py           # HITL 检测（前置+后置）
│   │   └── handoff.py            # 会话快照生成
│   ├── scripts/
│   │   └── import_knowledge.py   # 一键导入脚本
│   └── api/
│       └── routes.py             # FastAPI 接口
│
├── web/
│   └── app.py                    # Gradio 聊天界面 + HITL 人工接管
│
├── data/
│   ├── raw/                      # 原始 PDF 文件
│   ├── processed/                # 解析后的 Markdown
│   └── import_record.json        # 导入记录
│
├── chroma_db/                    # 向量数据库
├── changelogs/                   # 变更日志（16 份）
├── interview_highlights/         # 面试亮点文档
└── docs/
    └── architecture.png          # 系统架构图
```

---

## 技术架构

```
用户提问
    ↓
Gradio 界面（web/app.py）
    ↓
┌─────────────────────────────────────────────────┐
│  LangGraph 状态图（app/graph/builder.py）        │
│                                                   │
│  classifier_node                                  │
│    ├── 前置检测：系统控制意图（转人工/投诉/售后）   │
│    └── LLM 意图分类（产品/故障/培训/打招呼/未知）  │
│         ↓                                         │
│    ┌────┴────┬──────────┐                        │
│    ↓         ↓          ↓                        │
│  产品Agent  故障Agent  培训Agent                  │
│  (RAG检索)  (RAG检索)  (RAG检索)                  │
│    └─────────┴──────────┘                        │
│              ↓                                   │
│    hitl_checker_node（后置检测）                  │
│    ├── Agent 拒绝？                              │
│    ├── 置信度低？                                │
│    └── 敏感内容？                                │
│              ↓                                   │
│            END                                   │
└─────────────────────────────────────────────────┘
    ↓
HITL 触发？ → 会话快照 → 人工接管模式
```

---

## 工作亮点

### 1. 双层 HITL 架构

**问题**：单一检测层无法覆盖所有场景

**解决方案**：前置规则检测 + 后置兜底检测

| 层级 | 位置 | 检测方式 | 覆盖场景 |
|------|------|---------|---------|
| 前置 | classifier_node | 规则匹配（毫秒级） | 转人工、投诉、售后 |
| 后置 | hitl_checker_node | Agent 回答分析 | 拒绝回答、低置信度、敏感内容 |

**代码位置**：`app/hitl/detector.py` + `app/graph/nodes.py`

### 2. 会话快照（Session Snapshot）

**问题**：人工客服接手时是"空白状态"，不知道用户之前聊了什么

**解决方案**：LLM 从 State 提取结构化快照

```python
{
    "core_need": "用户温湿度传感器指示灯不亮",
    "hitl_reason": "Agent 拒绝回答",
    "suggested_plan": "1. 确认接线 2. 检查供电 3. 远程协助"
}
```

**代码位置**：`app/hitl/handoff.py`

### 3. 人工接管模式

**问题**：人工回复一次后，系统又把后续消息交给 AI，形成死循环

**解决方案**：`_hitl_active` 标志位，人工完全接管直到说「关闭」

```
用户提问 → HITL 触发 → 显示快照
    ↓
人工回复 → "[人工客服] xxx"（所有后续消息走人工）
人工说"关闭" → 退出人工模式，恢复 AI
```

**代码位置**：`web/app.py`

### 4. LLM Fallback 兜底机制

**问题**：DeepSeek API 偶发 503 错误，服务不可用

**解决方案**：主备模型自动切换架构
- 主模型：DeepSeek（deepseek-chat）
- 备用模型：通义千问（qwen-plus）
- 自动故障检测：捕获超时和 5xx 错误
- 透明切换：用户无感知，自动回退

**代码位置**：`app/llm/models.py`

### 5. 知识库增量同步机制

**问题**：每次添加/修改文档都要全量重建，效率低

**解决方案**：类比 Git 工作流的增量同步
- `data/raw/` = 工作目录（用户放 PDF）
- `data/processed/` = 暂存区（解析后的 MD）
- `chroma_db/` = 仓库（向量化存储）
- `import_record.json` = 提交历史

**代码位置**：`app/scripts/import_knowledge.py` + `app/rag/imported_files.py`

---

## 遇到的问题和解决方案

### 问题 1：系统控制意图被 LLM 吞掉

**现象**：用户说"转人工"，被 LLM 分类为"未知意图"

**原因**：LLM 分类器把系统控制意图当作业务意图处理

**解决**：前置规则检测，在 LLM 分类之前拦截

### 问题 2：LangGraph interrupt 后 State 不更新

**现象**：会话快照在后端生成成功，但前端不展示

**原因**：`interrupt()` 暂停图执行时，节点返回值不合并到 State

**解决**：HITL 检测从 graph 内部移到 web 层，直接用 detector 函数检测

### 问题 3：HITL 死循环

**现象**：人工回复一次后，系统又触发 HITL

**原因**：人工回复后 graph 恢复，重新进入检测流程

**解决**：添加 `_hitl_active` 标志，一旦激活人工接管，所有消息走人工

### 问题 4：向量维度不匹配

**现象**：检索时报错维度不匹配（384 vs 768）

**原因**：之前使用本地模型（384 维），后来改为通义千问 API（768 维）

**解决**：删除旧的 ChromaDB 数据，重新导入

### 问题 5：DeepSeek 503 错误

**现象**：`{"error":{"message":"Service is too busy","code":"503"}}`

**原因**：DeepSeek API 服务繁忙

**解决**：实现 Fallback 机制，自动切换到通义千问

---

## 知识库管理

### 添加新文档

```bash
# 1. 把 PDF 放到 data/raw/ 目录（支持子目录）
mkdir data/raw/新产品
cp 新产品手册.pdf data/raw/新产品/

# 2. 运行导入脚本
python app/scripts/import_knowledge.py

# 3. 完成！问答系统自动识别新文档
python web/app.py
```

### 更新文档

```bash
# 直接替换 PDF 文件，脚本自动检测修改时间并重新导入
cp 新版本手册.pdf data/raw/新产品/新产品手册.pdf -y
python app/scripts/import_knowledge.py
```

### 删除文档

```bash
# 删除 PDF 文件
del data\raw\新产品\新产品手册.pdf

# 运行脚本自动清理残留
python app/scripts/import_knowledge.py
```

### 查看状态

```bash
python app/scripts/import_knowledge.py --status
```

### 强制重建

```bash
python app/scripts/import_knowledge.py --force
```

---

## 开发路线图

| 阶段 | 状态 | 说明 |
|------|------|------|
| Phase 1 - 单 Agent RAG | ✅ 已完成 | 基础问答系统 |
| Phase 2 - 多 Agent 协作 | ✅ 已完成 | LangGraph 路由 + 意图分类 |
| Phase 3 - 记忆系统 | ✅ 已完成 | LangGraph State 集成 |
| Phase 4 - 查询优化 |   待开始 | Query Rewriting |
| Phase 5 - 人工审核 | ✅ 已完成 | HITL 双层检测 + 会话快照 |
| Phase 6 - 知识库后台 |   待开始 | 管理界面 |
| Phase 7 - 部署优化 |   待开始 | 监控、日志 |

---

## 相关文档

- `changelogs/` - 变更日志（16 份，记录每个步骤的改动）
- `interview_highlights/` - 面试亮点文档
  - `01_llm_fallback_mechanism.md` - LLM Fallback 机制
  - `02_knowledge_base_management.md` - 知识库增量管理
  - `03_hitl_architecture.md` - HITL 双层架构
  - `07_hitl_session_handoff.md` - 会话快照 + 人工接管
- `docs/architecture.png` - 系统架构图

---

## 联系方式

如有问题，请查看 `changelogs/` 目录下的变更日志，或参考 `interview_highlights/` 中的设计文档。
