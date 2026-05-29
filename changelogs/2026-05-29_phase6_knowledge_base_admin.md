# 改动摘要：Phase 6 知识库管理后台

**日期**：2026-05-29
**操作人**：Claude
**任务**：实现知识库管理后台，支持非技术人员通过 Web 界面管理文档

---

## 改动文件列表

### 新增文件

| 文件 | 说明 |
|---|---|
| `web/admin.py` | 知识库管理后台 Gradio 界面 |

### 修改文件

| 文件 | 说明 |
|---|---|
| `app/rag/retriever.py` | 每次查询重新加载 ChromaDB，确保数据最新 |
| `app/rag/imported_files.py` | 修复向量数据删除逻辑，支持模糊匹配 |
| `app/agents/base.py` | 处理 metadata 为 None 的情况，防止崩溃 |
| `PROJECT_DESIGN.md` | 更新 Phase 6 详细计划 |

---

## 功能说明

### 知识库管理后台（web/admin.py）

| 功能 | 说明 |
|------|------|
| 上传文档 | 选择 PDF → 保存到 data/raw/ → 自动调用 MinerU 解析 → 向量化存储 |
| 文档列表 | 显示已导入文档的文件名、状态、chunk 数、导入时间 |
| 删除文档 | 删除 PDF 文件 + MD 目录 + 向量数据 + 导入记录 |
| 刷新列表 | 手动刷新文档列表和下拉框选项 |

### 界面设计

```
┌─────────────────────────────────────────┐
│  上传文档                               │
│  [选择文件] [上传并处理]                 │
│                                         │
│  删除文档                               │
│  [选择文档] [删除]                       │
│                                         │
│  已导入文档                             │
│  [文件名 | 状态 | chunks | 时间]        │
│  [刷新列表]                             │
└─────────────────────────────────────────┘
```

---

## Bug 修复

### 1. 删除后向量数据未清理

**问题**：`delete_vector_data()` 构建的 source 格式与实际存储不匹配，导致删除失败。

**解决**：精确匹配失败时，改用模糊匹配（检查 source 是否包含文件名）。

```python
# 精确匹配
collection.delete(where={"source": source})

# 如果失败，模糊匹配
for meta in all_data['metadatas']:
    if pdf_name_no_ext in meta.get('source', ''):
        ids_to_delete.append(...)
```

### 2. 删除后客服系统崩溃

**问题**：管理后台删除文档后，客服系统查询时 metadata 为 None，导致 AttributeError。

**解决**：在 `_two_step_retrieve()` 中添加安全检查，跳过 metadata 为 None 的结果。

```python
metadata = r.get("metadata")
if metadata is None:
    print(f"[Agent] 警告：跳过 metadata 为空的结果")
    continue
```

### 3. 删除后客服系统数据不更新

**问题**：管理后台和客服系统是独立进程，各自缓存了 ChromaDB 内存副本，删除后客服系统仍用旧数据。

**解决**：修改 `get_vectorstore()` 函数，每次调用都重新创建客户端，读取磁盘最新数据。

```python
def get_vectorstore():
    # 每次重新创建客户端，读取磁盘最新数据
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
```

---

## 复用模块

知识库后台复用了现有模块，没有重新实现：

| 模块 | 函数 | 用途 |
|------|------|------|
| `imported_files.py` | `get_imported_files()` | 获取文档列表 |
| `imported_files.py` | `get_import_stats()` | 获取统计信息 |
| `imported_files.py` | `delete_file_record()` | 删除记录和向量数据 |
| `import_knowledge.py` | `import_single_file()` | 导入单个文件 |

---

## 测试验证

| 测试场景 | 预期结果 | 实际结果 |
|----------|---------|---------|
| 上传 PDF | 文档出现在列表中 | ✅ |
| 删除文档 | PDF + MD + 向量数据全部清理 | ✅ |
| 删除后客服查询 | 不崩溃，回答"没找到" | ✅ |
| 删除后客服查询 | 立即感知数据变化 | ✅ |
