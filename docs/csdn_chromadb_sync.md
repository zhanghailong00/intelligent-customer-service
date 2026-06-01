# RAG 系统踩坑：管理后台删除文档后，客服系统崩了

## 前言

在构建基于 RAG 的智能客服系统时，我遇到了一个隐蔽的 bug：通过管理后台删除文档后，客服系统查询相同问题时直接崩溃，报错 `AttributeError: 'NoneType' object has no attribute 'get'`。

重启客服系统后恢复正常。

这个问题困扰了我一段时间，最终发现是**独立进程间的向量数据库缓存不一致**导致的。这篇文章记录了问题的发现、分析和解决过程。

---

## 一、系统架构

我的智能客服系统有两个独立进程：

```
进程 1：管理后台（web/admin.py）
    └── 上传/删除文档 → 修改 ChromaDB

进程 2：客服系统（web/app.py）
    └── 用户提问 → 查询 ChromaDB → 生成回答
```

两个进程共享同一个 ChromaDB 磁盘目录（`chroma_db/`），但各自在内存中维护了一份副本。

```
┌─────────────┐     ┌─────────────┐
│  管理后台    │     │  客服系统    │
│  内存副本 A  │     │  内存副本 B  │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └───────┬───────────┘
               │
        ┌──────┴──────┐
        │  chroma_db/  │  ← 磁盘上的数据
        │  (SQLite)    │
        └─────────────┘
```

---

## 二、问题现象

### 2.1 正常流程

```
用户提问："传感器不亮了怎么办"
    ↓
检索 ChromaDB → 找到 3 篇相关文档
    ↓
LLM 生成回答 → "请按以下步骤排查..."
```

### 2.2 异常流程

```
管理后台删除文档
    ↓
用户提问："传感器不亮了怎么办"
    ↓
检索 ChromaDB → 找到 3 篇"幽灵文档"（已被删除但内存中还在）
    ↓
metadata 为 None → AttributeError → 崩溃
```

### 2.3 错误日志

```
AttributeError: 'NoneType' object has no attribute 'get'

File "app/agents/base.py", line 114, in _two_step_retrieve
    source = r["metadata"].get("source", "")
             ^^^^^^^^^^^^^^^^^
```

---

## 三、根因分析

### 3.1 ChromaDB 的工作方式

ChromaDB 是嵌入式数据库，类似 SQLite：

| 特性 | 说明 |
|------|------|
| 存储 | 数据保存在磁盘（chroma_db/ 目录） |
| 加载 | 启动时加载到内存 |
| 缓存 | 进程内维护内存副本 |

### 3.2 问题根源

```
时间线：
T1: 客服系统启动 → 加载 ChromaDB 到内存副本 B
T2: 管理后台删除文档 → 修改磁盘数据
T3: 客服系统查询 → 用内存副本 B（还是旧数据）
T4: 内存中有已删除文档的记录，但实际数据已不存在
T5: metadata 为 None → 崩溃
```

### 3.3 为什么不直接读磁盘？

ChromaDB 为了性能，启动时加载数据到内存，后续查询走内存缓存。这是合理的设计，但在多进程场景下会导致数据不一致。

---

## 四、解决方案

### 4.1 方案对比

| 方案 | 说明 | 优点 | 缺点 |
|------|------|------|------|
| A. 错误处理 | metadata 为 None 时跳过 | 简单，防崩溃 | 不解决数据不一致 |
| B. 每次查询重新加载 | 每次查询前重新创建 ChromaDB 客户端 | 数据实时最新 | 有性能开销 |
| C. API 通知 | 管理后台调用客服 API 触发重新加载 | 精确控制 | 实现复杂 |

### 4.2 最终方案：A + B 组合

**方案 B：每次查询重新加载**

```python
def get_vectorstore():
    """
    每次调用都重新创建客户端，确保读取磁盘最新数据
    """
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
```

**方案 A：错误处理兜底**

```python
for r in results:
    # 安全检查：metadata 可能为 None
    metadata = r.get("metadata")
    if metadata is None:
        print(f"[Agent] 警告：跳过 metadata 为空的结果")
        continue
    source = metadata.get("source", "")
```

### 4.3 性能分析

ChromaDB 重新加载的性能开销：

| 操作 | 耗时 |
|------|------|
| ChromaDB 重新加载 | 10-50ms |
| Embedding API 调用 | 200-500ms |
| LLM 回答生成 | 1-3 秒 |
| **总响应时间** | **2-4 秒** |

**结论**：ChromaDB 重新加载只占总时间的 1-2%，影响可忽略。

---

## 五、向量数据删除的坑

### 5.1 问题

删除文档时，需要同时清理三样东西：
1. PDF 文件（data/raw/）
2. Markdown 文件（data/processed/）
3. 向量数据（ChromaDB）

前两个用文件路径删除，很简单。但第三个有问题。

### 5.2 source 字段格式不匹配

ChromaDB 中存储的 source 格式：

```
"02-实验环境的搭建\02-实验环境的搭建.md"
```

但删除时构建的格式可能不同：

```python
# 代码构建的格式
source = f"{pdf_name_no_ext}\\{pdf_name_no_ext}.md"

# 如果 PDF 在子目录中，实际格式是
# "子目录\文件名\文件名.md"
```

格式不匹配 → 删除失败 → 向量数据残留。

### 5.3 解决方案：模糊匹配

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

---

## 六、总结

### 核心要点

| 要点 | 说明 |
|------|------|
| **问题根源** | 独立进程各自缓存 ChromaDB 内存副本 |
| **解决方案** | 每次查询重新加载 + 错误处理兜底 |
| **性能影响** | ChromaDB 重新加载 10-50ms，可忽略 |
| **删除坑** | source 字段格式不匹配，用模糊匹配解决 |

### 适用场景

- RAG 系统有多个独立进程
- 管理后台和问答系统分离部署
- 需要实时更新知识库

### 经验教训

1. **嵌入式数据库的缓存机制**：SQLite、ChromaDB 等嵌入式数据库会在进程内缓存数据，多进程场景需要注意同步
2. **错误处理很重要**：即使数据理论上应该一致，也要加兜底逻辑
3. **性能取舍**：10-50ms 的重新加载开销，换来数据一致性，完全值得

---

## 文末结语

这个 bug 让我 debug 了一段时间，最终发现是 ChromaDB 的缓存机制在多进程场景下的陷阱。在 RAG 系统开发中，数据一致性问题容易被忽视，但一旦遇到就很隐蔽。

如果你的 RAG 系统也有多个独立进程，建议在查询前重新加载向量数据库，10-50ms 的开销换来数据一致性，非常值得。

---

**项目地址**：[GitHub 仓库链接]

**相关文章**：
- 《LangGraph interrupt() 暂停后 State 不更新？这个坑我帮你踩了》
- 《双层 HITL 架构：为什么你的 AI 客服需要前置规则 + 后置兜底？》
- 《RAG 查询优化实战：历史感知改写 + 两步检索，召回率提升 30%》
