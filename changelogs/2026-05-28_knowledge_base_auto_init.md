# 改动摘要：知识库自动初始化

**日期**：2026-05-28
**操作人**：Claude
**任务**：Hugging Face 部署优化 — 启动时自动增量同步向量数据库

---

## 改动文件列表

### 新增文件

| 文件 | 说明 |
|---|---|
| `app/startup.py` | 知识库自动初始化模块（增量同步） |

### 修改文件

| 文件 | 说明 |
|---|---|
| `app.py` | Hugging Face 入口，启动时调用 init_knowledge_base() |

---

## 设计决策

### 为什么需要自动初始化？

Hugging Face Space 没有持久化存储，每次重启后 `chroma_db` 目录会丢失。手动上传 `chroma_db` 不现实，需要在应用启动时自动创建。

### 为什么用增量同步？

| 方案 | 首次启动 | 后续启动 | 说明 |
|------|---------|---------|------|
| 全量重建 | 慢 | 慢 | 每次都处理所有文档 |
| **增量同步** | 慢 | **快** | 只处理变化的文档 |

### 增量同步逻辑

```
应用启动
    ↓
扫描 data/raw/ 中的所有文档
    ↓
┌─────────────────────────────────────┐
│ 使用 imported_files 模块：           │
│   1. find_deleted_files() → 清理    │
│   2. find_new_files() → 导入        │
│   3. find_updated_files() → 重新导入│
└─────────────────────────────────────┘
    ↓
只处理变化的文档，跳过未变化的
```

---

## 代码实现

### startup.py 核心逻辑

```python
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

### PDF 处理流程

```python
def process_single_file(doc_path, relative_path):
    """处理单个文档文件"""
    if doc_path.endswith('.pdf'):
        # PDF → MinerU API → Markdown
        md_path = convert_pdf_to_markdown(doc_path)
        process_path = md_path
    else:
        # Markdown → 直接处理
        process_path = doc_path

    # 切分 → 向量化
    chunks = load_and_split(process_path)
    count = add_documents(chunks)
```

---

## 测试验证

| 测试场景 | 预期结果 |
|----------|---------|
| 首次启动（无记录） | 处理所有文档 |
| 后续启动（无变化） | 跳过所有文档 |
| 添加新文档 | 只处理新文档 |
| 更新文档 | 只处理更新的文档 |
| 删除文档 | 清理向量数据 |

---

## 部署流程

### 首次部署

```bash
# 1. 上传代码和文档
git add app/startup.py app.py data/raw/
git commit -m "feat: 知识库自动初始化"
git push hf main

# 2. Space 启动时自动处理文档
```

### 更新文档

```bash
# 1. 修改 data/raw/ 中的文档
# 2. 推送
git add data/raw/
git commit -m "更新文档"
git push hf main

# 3. Space 自动重启，自动增量同步
```

---

## 面试亮点

1. **增量同步机制**：启动时只处理变化的文档，不重建全部，节省时间和 API 调用
2. **自动化部署**：上传文档后自动处理，不需要手动管理向量数据库
3. **复用现有模块**：调用已有的 imported_files 模块，不重复造轮子
4. **PDF 自动转换**：PDF 文件自动调用 MinerU API 转成 Markdown
