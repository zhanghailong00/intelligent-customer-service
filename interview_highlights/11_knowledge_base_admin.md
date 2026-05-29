# 面试亮点：知识库管理后台 + 数据实时同步

---

## 一、问题背景

### 1.1 业务需求

公司售后团队需要能自己更新知识库文档，不能每次都找技术人员用 Git 命令操作。

### 1.2 技术挑战

1. 管理后台和客服系统是**独立进程**，数据同步问题
2. 向量数据库删除后，客服系统仍用旧数据，导致崩溃
3. Gradio 组件更新机制兼容性问题

---

## 二、方案设计

### 2.1 知识库管理后台

| 功能 | 说明 |
|------|------|
| 上传文档 | PDF → 保存 → MinerU 解析 → 向量化 |
| 删除文档 | PDF + MD + 向量数据 + 记录，全量清理 |
| 文档列表 | 实时显示导入状态和 chunk 数 |

### 2.2 数据实时同步方案

**问题**：管理后台删除文档后，客服系统仍用旧的内存数据。

**三种方案对比**：

| 方案 | 说明 | 选择 |
|------|------|------|
| A. 错误处理 | metadata 为 None 时跳过，防止崩溃 | ✅ 采用 |
| B. 每次查询重新加载 | 每次查询前重新创建 ChromaDB 客户端 | ✅ 采用 |
| C. API 通知 | admin 调用客服 API 触发重新加载 | 过于复杂 |

**最终方案：A + B 组合**
- B 保证数据最新（每次读磁盘）
- A 防止极端情况崩溃（兜底）

### 2.3 性能分析

| 操作 | 耗时 |
|------|------|
| ChromaDB 重新加载 | 10-50ms |
| Embedding API 调用 | 200-500ms |
| LLM 回答生成 | 1-3 秒 |
| **总响应时间** | **2-4 秒** |

ChromaDB 重新加载只占总时间的 1-2%，影响可忽略。

---

## 三、技术实现

### 3.1 向量数据删除（模糊匹配）

```python
def delete_vector_data(record):
    # 先尝试精确匹配
    collection.delete(where={"source": source})
    
    # 如果失败，模糊匹配
    all_data = collection.get(include=['metadatas'])
    ids_to_delete = []
    for i, meta in enumerate(all_data['metadatas']):
        if pdf_name_no_ext in meta.get('source', ''):
            ids_to_delete.append(all_data['ids'][i])
    
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
```

### 3.2 数据实时同步

```python
def get_vectorstore():
    """每次调用都重新创建客户端，确保读取最新数据"""
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
```

### 3.3 错误处理

```python
for r in results_original + results_rewritten:
    metadata = r.get("metadata")
    if metadata is None:
        print(f"[Agent] 警告：跳过 metadata 为空的结果")
        continue
    source = metadata.get("source", "")
```

---

## 四、面试话术

### 4.1 项目描述

> "我实现了知识库管理后台，非技术人员可以通过 Web 界面上传和删除文档。技术难点在于管理后台和客服系统是独立进程，删除文档后客服系统仍用旧数据。我采用了双重方案：每次查询重新加载 ChromaDB 保证数据最新，同时加错误处理防止极端情况崩溃。ChromaDB 重新加载只需 10-50ms，对性能影响可忽略。"

### 4.2 技术细节

> "向量数据删除也踩了坑。ChromaDB 中的 source 字段格式是'目录名\\文件名.md'，但删除时构建的格式可能不匹配。我先用精确匹配，失败后改用模糊匹配，遍历所有 metadata 找到包含文件名的记录再删除。"

### 4.3 延伸讨论

| 面试官可能问 | 可以聊的方向 |
|-------------|-------------|
| 为什么不共享 ChromaDB 实例？ | 独立进程无法共享内存，只能通过磁盘同步 |
| 为什么不用 API 通知？ | 增加复杂度，性能收益不明显 |
| 还有什么优化空间？ | 可以加文件监听，只在数据变化时重新加载 |
| 多用户并发怎么办？ | ChromaDB 支持并发读，写操作加锁 |

---

## 五、核心要点

| 要点 | 说明 |
|------|------|
| **数据实时同步** | 每次查询重新加载 ChromaDB，确保数据最新 |
| **错误处理** | metadata 为 None 时跳过，防止崩溃 |
| **模糊匹配删除** | 精确匹配失败时用模糊匹配，确保向量数据清理干净 |
| **性能可控** | ChromaDB 重新加载只需 10-50ms，影响可忽略 |

---

## 六、一句话总结

> "独立进程间通过磁盘同步数据，每次查询重新加载保证最新，错误处理兜底防崩溃。"
