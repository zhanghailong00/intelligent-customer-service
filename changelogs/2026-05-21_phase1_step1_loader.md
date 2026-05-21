# 改动摘要：Phase 1 第 1 步 - 文档加载和切分

**日期**：2026-05-21
**操作人**：Claude
**任务**：实现 Markdown 文档加载和按标题切分

---

## 改动文件列表

### 1. 新增文件

| 文件 | 说明 |
|---|---|
| `app/rag/loader.py` | 文档加载和切分模块 |
| `tests/test_loader.py` | 文档切分测试脚本 |

### 2. 移动文件

| 原位置 | 新位置 | 说明 |
|---|---|---|
| `test_api.py` | `tests/test_api.py` | 测试脚本整理到 tests 目录 |
| `test_embedding.py` | `tests/test_embedding.py` | 测试脚本整理到 tests 目录 |
| `test_mineru.py` | `tests/test_mineru.py` | 测试脚本整理到 tests 目录 |

### 3. 修改文件

| 文件 | 修改内容 |
|---|---|
| `tests/test_api.py` | 添加 sys.path 设置 |
| `tests/test_embedding.py` | 添加 sys.path 设置 |
| `tests/test_mineru.py` | 添加 .env 路径设置 |
| `tests/test_loader.py` | 修复文件路径（使用绝对路径） |

---

## 每个文件的改动详情

### app/rag/loader.py（新增）

**功能**：Markdown 文档加载和按标题切分

**核心函数**：
- `load_markdown(file_path)`: 读取 Markdown 文件
- `split_by_headers(content, source_file)`: 按标题层级切分
- `_set_parent_chapters(chunks)`: 设置上级标题
- `_clean_chunks(chunks)`: 清理内容（移除 `<details>` 标签）
- `load_and_split(file_path)`: 加载并切分

**切分规则**：
- 遇到 # ## ### 标题时创建新 chunk
- 每个标题下的内容是一个 chunk
- 自动提取元数据（来源、章节、上级标题）

**为什么这样设计**：
- 按标题切分保持语义完整性
- 元数据便于后续检索和展示
- 清理 `<details>` 标签避免噪声

---

### tests/test_loader.py（新增）

**功能**：测试文档切分效果

**测试内容**：
- 加载 Markdown 文件
- 验证切分结果（3 个 chunk）
- 验证元数据正确性

---

### tests/test_*.py（修改）

**修改内容**：
- 添加 `sys.path.insert(0, ...)` 设置
- 确保从 tests/ 目录运行时能正确导入 app 模块
- 使用绝对路径（`PROJECT_ROOT`）确保文件路径正确
- 添加文件存在性检查

---

## 潜在风险

| 风险 | 说明 | 缓解措施 |
|---|---|---|
| 标题层级误判 | 如果 Markdown 格式不规范，可能切分错误 | 单元测试覆盖各种格式 |
| 中文编码问题 | Windows 终端可能显示乱码 | 已添加 encoding="utf-8" |
| 空 chunk | 如果标题下没有内容，会生成空 chunk | 已在代码中过滤空 chunk |
| 文件路径问题 | 从 tests/ 目录运行时路径错误 | 已使用绝对路径（PROJECT_ROOT） |

---

## 建议测试

### 1. 单元测试

```bash
# 运行文档切分测试
python tests/test_loader.py
```

**预期结果**：
- 切分为 3 个 chunk
- 元数据正确（来源、章节、上级标题）
- `<details>` 标签已清理

### 2. 边界测试

- 测试空文件
- 测试没有标题的文件
- 测试多级标题（# ## ###）

### 3. 集成测试

- 测试从 PDF 解析到切分的完整流程

---

## 接口兼容性

| 接口 | 状态 | 说明 |
|---|---|---|
| `load_and_split(file_path)` | 新增 | 无兼容性问题 |
| 元数据结构 | 新增 | 无兼容性问题 |

---

## 回滚方案

如果出现问题，可以：
1. 删除 `app/rag/loader.py`
2. 删除 `tests/test_loader.py`
3. 恢复测试脚本到根目录

---

## 下一步

Phase 1 第 2 步：向量化存储（通义千问 Embedding + ChromaDB）
