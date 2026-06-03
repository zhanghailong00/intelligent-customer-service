# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

嵌入式实训箱智能客服系统 - 面向高校实训设备的智能客服平台，基于 **多 Agent + RAG + HITL** 架构实现产品知识问答、故障排查、培训指导等功能。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 Gradio 用户对话界面（端口 7860）
python web/app.py

# 启动知识库管理后台（端口 7861）
python web/admin.py

# 导入知识库（PDF 文件放到 data/raw/ 目录后执行）
python app/scripts/import_knowledge.py

# 查看导入状态
python app/scripts/import_knowledge.py --status

# 强制重新导入所有文档
python app/scripts/import_knowledge.py --force

# 运行测试
python -m pytest tests/
```

## 技术栈

- **LLM**：DeepSeek API（主模型）+ 通义千问（备用模型），自动 Fallback
- **向量数据库**：ChromaDB（嵌入式，数据存放在 `chroma_db/` 目录）
- **Embedding**：通义千问 text-embedding-v3
- **AI 框架**：LangChain + LangGraph
- **Web 框架**：FastAPI + Gradio
- **文档处理**：MinerU API（PDF 转 Markdown）

## 项目架构

```
用户提问
    ↓
Gradio 界面（web/app.py）
    ↓
LangGraph 状态图（app/graph/builder.py）
    ├── classifier_node：前置规则检测 + LLM 意图分类
    ├── product/fault/training_agent_node：Agent 处理（RAG 检索 + LLM 生成）
    └── hitl_checker_node：后置兜底检测（拒绝/低置信度/敏感内容）
    ↓
HITL 触发？ → 会话快照 → 人工接管模式
```

## 核心模块

| 模块 | 路径 | 职责 |
|------|------|------|
| **LLM** | `app/llm/models.py` | 模型封装 + Fallback 机制 |
| **意图分类** | `app/llm/intent_classifier.py` | LLM 意图分类（产品/故障/培训/打招呼/未知） |
| **Agent 基类** | `app/agents/base.py` | 查询改写 + 两步检索 + LLM 生成 |
| **LangGraph** | `app/graph/` | 状态图定义、节点函数、路由逻辑 |
| **HITL** | `app/hitl/` | 双层检测 + 会话快照生成 |
| **RAG** | `app/rag/` | 文档加载、向量化、检索 |
| **知识库管理** | `app/rag/imported_files.py` | 导入记录、增量同步 |

## 关键设计决策

1. **双层 HITL 架构**：前置规则检测（毫秒级）+ 后置兜底检测，覆盖转人工、投诉、售后等场景
2. **LLM Fallback**：DeepSeek 调用失败时自动切换到通义千问，用户无感知
3. **查询重写**：基于历史对话上下文改写用户问题，解决多轮对话中代词和省略主语问题
4. **两步检索**：原始 query + 改写后 query 分别检索，合并去重，提升召回率
5. **会话快照**：HITL 触发时，LLM 提取核心诉求和建议方案，传递给人工客服

## 数据目录

```
data/
├── raw/                      # 原始 PDF 文件（用户放入）
├── processed/                # 解析后的 Markdown（MinerU 生成）
└── import_record.json        # 导入记录（避免重复导入）

chroma_db/                    # ChromaDB 向量数据库
```

## 注意事项

- 代码注释使用中文
- Git 提交信息格式：`feat/fix/refactor: 简短描述`
- 不要自动提交 git，只提供命令让用户自己执行
- 知识库文档必须先转换为 Markdown 格式再导入
- MinerU API 需要配置 `MINERU_TOKEN` 环境变量
