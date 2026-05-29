# 面试亮点：知识库自动初始化 + 增量同步

---

## 一、问题背景

### 1.1 部署痛点

Hugging Face Space 没有持久化存储：
- 每次重启后 `chroma_db` 目录丢失
- 手动上传 `chroma_db` 不现实
- 文档更新后需要重新构建向量数据库

### 1.2 目标

1. 应用启动时自动创建向量数据库
2. 只处理变化的文档（增量同步）
3. 更新文档后自动生效

---

## 二、方案设计

### 2.1 全量重建 vs 增量同步

| 方案 | 首次启动 | 后续启动 | API 调用 | 说明 |
|------|---------|---------|---------|------|
| 全量重建 | 慢 | 慢 | 多 | 每次都处理所有文档 |
| **增量同步** | 慢 | **快** | **少** | 只处理变化的文档 |

### 2.2 增量同步逻辑

```
应用启动
    ↓
扫描 data/raw/ 中的所有文档
    ↓
┌─────────────────────────────────────┐
│ 对比 import_record.json 记录：       │
│                                     │
│ 新增：PDF 存在但没记录 → 导入       │
│ 更新：修改时间变了 → 重新导入       │
│ 删除：有记录但 PDF 不存在 → 清理    │
│ 未变化：跳过                        │
└─────────────────────────────────────┘
    ↓
只处理变化的部分
```

### 2.3 PDF 处理流程

```
PDF 文件
    ↓
MinerU API 解析
    ↓
生成 Markdown
    ↓
load_and_split 切分
    ↓
Embedding API 向量化
    ↓
存入 ChromaDB
```

---

## 三、技术实现

### 3.1 模块设计

```
app/
├── startup.py          # 知识库自动初始化模块
├── rag/
│   ├── imported_files.py  # 导入记录管理（已有）
│   ├── loader.py          # 文档加载（已有）
│   └── vectorstore.py     # 向量存储（已有）
└── scripts/
    └── import_knowledge.py # MinerU API 调用（已有）
```

### 3.2 核心代码

```python
# app/startup.py

def init_knowledge_base():
    """启动时自动初始化知识库（增量同步）"""
    # 1. 扫描文档
    doc_files = scan_document_files(raw_dir)

    # 2. 清理已删除的文件
    cleanup_deleted_files()

    # 3. 处理新增和更新的文件
    processed_count = process_new_and_updated_files(doc_files)

    # 4. 显示统计信息
    stats = get_import_stats()
```

### 3.3 复用现有模块

```python
from app.rag.imported_files import (
    find_deleted_files,    # 查找已删除文件
    find_new_files,        # 查找新增文件
    find_updated_files,    # 查找更新文件
    delete_file_record,    # 删除文件记录
    is_imported,           # 检查是否已导入
    is_file_updated,       # 检查是否更新
    mark_imported          # 标记已导入
)
```

---

## 四、部署流程

### 4.1 首次部署

```bash
# 1. 上传代码和文档
git add app/startup.py app.py data/raw/
git commit -m "feat: 知识库自动初始化"
git push hf main

# 2. Space 启动时自动处理文档
# 控制台输出：
# [Startup] 扫描到 4 个文档文件
# [Startup] [新增] 01-xxx.pdf
# [Startup] [新增] 02-xxx.pdf
# [Startup] 知识库初始化完成
#   已导入文件：4 个
#   总 chunk 数：20 个
```

### 4.2 更新文档

```bash
# 1. 修改 data/raw/ 中的文档
# 2. 推送
git add data/raw/
git commit -m "更新文档"
git push hf main

# 3. Space 自动重启，自动增量同步
# 控制台输出：
# [Startup] [更新] 02-xxx.pdf
# [Startup] 知识库初始化完成
```

---

## 五、面试话术

### 5.1 项目描述

> "Hugging Face Space 没有持久化存储，向量数据库会丢失。我实现了知识库自动初始化模块，应用启动时自动检测文档变化，增量更新向量数据库。复用了已有的 imported_files 模块，只处理新增和更新的文档，节省时间和 API 调用。"

### 5.2 技术细节

> "增量同步的核心是对比当前文档和 import_record.json 中的记录。新增文件直接导入，更新文件（修改时间变化）重新导入，已删除文件清理向量数据。PDF 文件会先调用 MinerU API 转成 Markdown，再进行切分和向量化。"

### 5.3 延伸讨论

| 面试官可能问 | 可以聊的方向 |
|-------------|-------------|
| 为什么不用全量重建？ | 全量重建每次都要处理所有文档，浪费时间和 API 调用 |
| 如何检测文件更新？ | 对比文件修改时间和 import_record.json 中的记录 |
| PDF 怎么处理？ | 调用 MinerU API 转成 Markdown，再切分向量化 |
| 向量数据库用什么？ | ChromaDB，嵌入式、零配置、适合中小规模 |

---

## 六、核心要点

| 要点 | 说明 |
|------|------|
| **增量同步** | 只处理变化的文档，不重建全部 |
| **自动初始化** | 启动时自动检测并处理文档 |
| **复用模块** | 调用已有的 imported_files 模块 |
| **PDF 转换** | 自动调用 MinerU API 转成 Markdown |

---

## 七、一句话总结

> "启动时自动增量同步向量数据库，只处理变化的文档，复用已有模块，实现自动化部署。"
