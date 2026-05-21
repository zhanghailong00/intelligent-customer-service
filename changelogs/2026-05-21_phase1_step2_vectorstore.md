# 改动摘要：Phase 1 第 2 步 - 向量化存储

**日期**：2026-05-21
**操作人**：Claude
**任务**：实现文档向量化并存入 ChromaDB

---

## 改动文件列表

### 1. 新增文件

| 文件 | 说明 |
|---|---|
| `app/rag/vectorstore.py` | 向量化存储模块 |
| `tests/test_vectorstore.py` | 向量化存储测试脚本 |

---

## 每个文件的改动详情

### app/rag/vectorstore.py（新增）

**功能**：将文档 chunks 向量化并存入 ChromaDB

**核心函数**：
- `get_embeddings(texts)`: 批量获取文本的向量表示
- `get_vectorstore()`: 获取 ChromaDB 实例
- `add_documents(chunks)`: 将 chunks 向量化并存储
- `clear_vectorstore()`: 清空向量数据库
- `get_vectorstore_stats()`: 获取统计信息

**技术细节**：
- 使用 dashscope SDK 调用通义千问 Embedding API
- 模型：tongyi-embedding-vision-flash-2026-03-06
- 向量维度：768
- 批量处理：每批 25 条，避免 API 限流
- 余弦相似度（cosine）用于向量检索

**为什么这样设计**：
- 批量处理提高效率，减少 API 调用次数
- 0.5 秒间隔避免触发限流
- 使用 dashscope SDK 而非 OpenAI 兼容模式（模型不支持）

---

### tests/test_vectorstore.py（新增）

**功能**：测试向量化存储完整流程

**测试内容**：
- 加载 Markdown 文件
- 切分为 chunks
- 清空旧数据
- 调用 Embedding API 向量化
- 存入 ChromaDB
- 验证统计信息

**测试结果**：
- 切分为 3 个 chunk
- 向量维度：768
- 存储成功，耗时 0.94 秒
- ChromaDB 统计：3 个文档

---

## 潜在风险

| 风险 | 说明 | 缓解措施 |
|---|---|---|
| API 限流 | 大量文档可能触发限流 | 批量处理 + 0.5 秒间隔 |
| 网络不稳定 | Embedding API 调用失败 | 已添加异常处理 |
| 向量维度不匹配 | 模型更换导致维度变化 | 配置文件统一管理模型名 |
| ChromaDB 冲突 | 重复运行导致数据重复 | 提供 clear_vectorstore() 函数 |

---

## 依赖关系

| 依赖 | 版本 | 用途 |
|---|---|---|
| dashscope | - | 通义千问 SDK |
| chromadb | - | 向量数据库 |

---

## 建议测试

### 1. 单元测试

```bash
# 运行向量化存储测试
python tests/test_vectorstore.py
```

**预期结果**：
- 切分为 3 个 chunk
- 向量维度：768
- 存储成功
- 统计信息正确

### 2. 边界测试

- 测试空文档
- 测试超长文本
- 测试 API 限流情况

### 3. 集成测试

- 测试从 PDF 解析到向量化的完整流程
- 测试检索功能（Phase 1 第 3 步）

---

## 接口兼容性

| 接口 | 状态 | 说明 |
|---|---|---|
| `add_documents(chunks)` | 新增 | 无兼容性问题 |
| `get_embeddings(texts)` | 新增 | 无兼容性问题 |
| `clear_vectorstore()` | 新增 | 无兼容性问题 |
| `get_vectorstore_stats()` | 新增 | 无兼容性问题 |

---

## 回滚方案

如果出现问题，可以：
1. 删除 `app/rag/vectorstore.py`
2. 删除 `tests/test_vectorstore.py`
3. 删除 `chroma_db/` 目录（可选）

---

## 下一步

Phase 1 第 3 步：向量检索（基于相似度的文档检索）
