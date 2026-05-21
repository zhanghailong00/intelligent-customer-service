# 智科云联 - 实训设备智能客服系统

面向高校实训设备（嵌入式实验箱）的智能客服平台，基于 RAG 技术实现产品知识问答、故障排查、培训指导等功能。

---

## 项目当前状态

**Phase 1（单 Agent RAG 系统）已完成** - 2026-05-21

已完成的功能：
- PDF 文档自动解析和向量化存储
- 语义检索和 RAG 问答
- LLM 主备模型自动切换（DeepSeek + 通义千问）
- 一键导入工具，支持增量同步
- Gradio 聊天界面和 FastAPI 接口

**下一步工作**：Phase 2 - 多 Agent 协作系统

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
│   │   └── models.py             # LLM 封装 + Fallback 机制
│   ├── rag/
│   │   ├── loader.py             # 文档加载和切分
│   │   ├── vectorstore.py        # 向量化存储（ChromaDB）
│   │   ├── retriever.py          # 向量检索
│   │   ├── qa_chain.py           # RAG 问答链
│   │   └── imported_files.py     # 导入记录管理
│   ├── scripts/
│   │   └── import_knowledge.py   # 一键导入脚本
│   └── api/
│       └── routes.py             # FastAPI 接口
│
├── web/
│   └── app.py                    # Gradio 聊天界面
│
├── data/
│   ├── raw/                      # 原始 PDF 文件
│   ├── processed/                # 解析后的 Markdown
│   └── import_record.json        # 导入记录
│
├── chroma_db/                    # 向量数据库
├── changelogs/                   # 变更日志
└── interview_highlights/         # 面试亮点文档
```

---

## 技术架构

```
用户提问
    ↓
Gradio/FastAPI 界面
    ↓
RAG 问答链 (qa_chain.py)
    ├── 向量检索 (retriever.py)
    │   ├── 通义千问 Embedding API（查询向量化）
    │   └── ChromaDB（相似度搜索）
    │
    └── LLM 生成 (models.py)
        ├── 主模型：DeepSeek API
        └── 备用模型：通义千问（自动切换）
    ↓
返回答案 + 参考来源
```

---

## 工作亮点

### 1. LLM Fallback 兜底机制

**问题**：DeepSeek API 偶发 503 错误，服务不可用

**解决方案**：主备模型自动切换架构
- 主模型：DeepSeek（deepseek-chat）
- 备用模型：通义千问（qwen-plus）
- 自动故障检测：捕获超时和 5xx 错误
- 透明切换：用户无感知，自动回退
- 状态追踪：`chat_with_fallback_status()` 返回调用详情

**代码位置**：`app/llm/models.py`

### 2. 知识库增量同步机制

**问题**：每次添加/修改文档都要全量重建，效率低

**解决方案**：类比 Git 工作流的增量同步
- `data/raw/` = 工作目录（用户放 PDF）
- `data/processed/` = 暂存区（解析后的 MD）
- `chroma_db/` = 仓库（向量化存储）
- `import_record.json` = 提交历史

**四种状态检测**：
| 状态 | 检测条件 | 处理方式 |
|------|----------|----------|
| 新增 | PDF 存在，JSON 无记录 | 自动导入 |
| 更新 | PDF 修改时间 > JSON 记录时间 | 重新导入 |
| 删除 | PDF 不存在，JSON 有记录 | 清理残留 |
| 无变化 | PDF 在，时间相同 | 跳过 |

**代码位置**：`app/scripts/import_knowledge.py` + `app/rag/imported_files.py`

### 3. Source 全局唯一性

**问题**：不同子目录下同名文件的向量数据互相覆盖

**解决方案**：source 使用完整相对路径
```python
# 之前：01-实验前准备.md（可能重复）
# 现在：实验箱前期准备工作\01-实验前准备\01-实验前准备.md（全局唯一）
```

### 4. 三层清理机制

**问题**：删除 PDF 后，MD 文件和向量数据残留

**解决方案**：联动清理三层数据
```python
delete_file_record(filename):
    1. delete_md_files()      # 删除 processed 目录
    2. delete_vector_data()   # 删除 ChromaDB 向量
    3. 从 JSON 移除记录
```

### 5. 孤立目录检测

**问题**：`--force` 清空记录后，processed 目录残留

**解决方案**：反向扫描 processed 目录，清理无对应记录的孤立 MD 目录

---

## 遇到的问题和解决方案

### 问题 1：向量维度不匹配

**现象**：检索时报错维度不匹配（384 vs 768）

**原因**：之前使用本地 sentence-transformers 模型（384 维），后来改为通义千问 Embedding API（768 维）

**解决**：删除旧的 ChromaDB 数据，重新导入

### 问题 2：DeepSeek 503 错误

**现象**：`{"error":{"message":"Service is too busy","code":"503"}}`

**原因**：DeepSeek API 服务繁忙

**解决**：实现 Fallback 机制，自动切换到通义千问

### 问题 3：Gradio API 不兼容

**现象**：`ChatInterface.__init__() got an unexpected keyword argument 'theme'`

**原因**：Gradio 6.x 版本 API 变更

**解决**：简化配置，移除不兼容参数

### 问题 4：MinerU 命令找不到

**现象**：`FileNotFoundError: [WinError 2] 系统找不到指定的文件`

**原因**：本地未安装 MinerU CLI

**解决**：改为使用 MinerU 在线 API（requests 调用）

### 问题 5：文件重命名冲突

**现象**：`FileExistsError: [WinError 183]`

**原因**：目标文件已存在

**解决**：重命名前先检查并删除已存在的目标文件

### 问题 6：向量数据库重复数据

**现象**：重复导入后，同文件的 chunk 数量翻倍

**原因**：ID 生成策略不唯一

**解决**：ID 格式改为 `{source_name}_chunk_{序号}`，导入前删除旧数据

### 问题 7：JSON 有记录但 PDF 更新

**现象**：更新 PDF 后运行脚本，没有重新导入

**原因**：旧记录缺少 `file_mtime` 字段

**解决**：`is_file_updated()` 自动补全旧记录的 mtime

### 问题 8：孤立 MD 目录残留

**现象**：删除 PDF 后运行 `--force`，processed 目录还有残留

**原因**：`--force` 清空了 JSON 记录，但没有清理 processed 目录

**解决**：新增 `find_orphan_md_dirs()` 函数，反向扫描清理

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

## API 接口

### POST /api/chat

```json
// 请求
{
    "message": "如何搭建实验环境？",
    "history": []
}

// 响应
{
    "answer": "根据文档，搭建实验环境需要...",
    "sources": ["02-实验环境的搭建.md"]
}
```

---

## 开发路线图

| 阶段 | 状态 | 说明 |
|------|------|------|
| Phase 1 - 单 Agent RAG | ✅ 已完成 | 基础问答系统 |
| Phase 2 - 多 Agent 协作 |   待开始 | LangGraph 路由 |
| Phase 3 - 记忆系统 |   待开始 | 多轮对话 |
| Phase 4 - 查询优化 |   待开始 | 意图识别、查询重写 |
| Phase 5 - 人工审核 |   待开始 | HITL 机制 |
| Phase 6 - 外部工具 |   待开始 | API 调用 |
| Phase 7 - 部署优化 |   待开始 | 监控、日志 |

---

## 相关文档

- `PROJECT_DESIGN.md` - 项目设计文档
- `changelogs/` - 变更日志（7 份）
- `interview_highlights/` - 面试亮点文档
  - `01_llm_fallback_mechanism.md` - LLM Fallback 机制
  - `02_knowledge_base_management.md` - 知识库增量管理

---

## 联系方式

如有问题，请查看 `changelogs/` 目录下的变更日志，或参考 `PROJECT_DESIGN.md` 中的详细设计。
