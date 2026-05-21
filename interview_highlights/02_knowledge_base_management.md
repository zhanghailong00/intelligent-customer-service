# 面试亮点：知识库增量管理与文件同步机制

**日期**：2026-05-21
**模块**：`app/scripts/import_knowledge.py` + `app/rag/imported_files.py`

---

## 核心设计思想

采用**声明式文件同步**思路，将知识库管理类比为 Git 的工作流：
- `data/raw/` 是"工作目录"（用户放 PDF 的地方）
- `data/processed/` 是"暂存区"（解析后的 Markdown）
- ChromaDB 是"仓库"（向量化的最终存储）
- `data/import_record.json` 是"提交历史"（记录每个文件的状态）

用户只需往 `data/raw/` 放文件、删文件，脚本自动完成增量同步，**零手动干预**。

---

## 四种状态检测机制

| 状态 | 检测条件 | 处理方式 |
|------|----------|----------|
| **新增** | PDF 存在，JSON 无记录 | MinerU 解析 → 向量化 → 记录 |
| **更新** | JSON 有记录，PDF 修改时间 > JSON 记录时间 | 删除旧 MD + 删除旧向量 → 重新导入 |
| **删除** | JSON 有记录，PDF 文件不存在 | 删除 MD 文件 + 删除向量数据 + 删除记录 |
| **无变化** | JSON 有记录，PDF 在，时间相同 | 跳过 |

---

## 关键技术实现

### 1. 文件修改时间检测（自动更新检测）

```python
# 通过对比 PDF 文件的修改时间与 JSON 中记录的时间来判断是否更新
def is_file_updated(filename, file_path):
    current_mtime = get_file_mtime(file_path)    # 获取 PDF 当前修改时间
    record_mtime = f.get("file_mtime", "")        # 获取 JSON 中记录的时间
    if current_mtime > record_mtime:
        return True   # 文件已更新
    return False
```

**设计亮点**：
- 利用操作系统文件修改时间（mtime），无需人工标记
- 时间格式统一为 ISO 8601，保证跨平台兼容
- 自动补全旧记录中缺失的 mtime 字段，向后兼容

### 2. 增量同步（幂等性设计）

```python
# 每次导入前先删除同 source 的旧数据，再插入新数据
collection.delete(where={"source": source})  # 删旧向量
collection.add(ids=ids, embeddings=embeddings, ...)  # 加新向量
```

**设计亮点**：
- 重复运行脚本不会产生重复数据（幂等性）
- 通过 source 字段精确删除单个文件的旧数据，不影响其他文件

### 3. 目录结构一致性

```
data/raw/                           data/processed/
├── 实验箱前期准备工作/              ├── 实验箱前期准备工作/
│   ├── 01-实验前准备.pdf            │   ├── 01-实验前准备/
│   └── 02-实验环境搭建.pdf          │   │   └── 01-实验前准备.md
                                    │   └── 02-实验环境搭建/
                                    │       └── 02-实验环境搭建.md
```

**设计亮点**：
- raw 和 processed 保持一致的子目录结构
- 支持无限层级的子目录嵌套
- 通过 `os.path.relpath()` 自动计算相对路径

### 4. 三层清理机制（删除联动）

```python
def delete_file_record(filename):
    # 1. 删除 MD 文件（data/processed/ 下对应的目录）
    delete_md_files(record)
    # 2. 删除向量数据（ChromaDB 中该 source 的所有 chunk）
    delete_vector_data(record)
    # 3. 删除 JSON 记录
    save_record(record)
```

**设计亮点**：
- 三层联动清理，不留残余数据
- 磁盘（MD）和内存（向量）同时清理
- 清理过程有日志输出，便于排查

### 5. 唯一 ID 与 Source 生成策略

```python
# source = 完整相对路径（含子目录），确保全局唯一
# 例如："实验箱前期准备工作\01-实验前准备\01-实验前准备.md"
source_file = os.path.relpath(file_path, processed_dir).replace("/", "\\")

# ID = source + chunk 序号，确保全局唯一
source_name = os.path.splitext(source)[0]
ids = [f"{source_name}_chunk_{i:04d}" for i in range(len(chunks))]
```

**设计亮点**：
- source 使用完整相对路径，不同子目录下同名文件不会冲突
- 不同文件的 chunk 不会 ID 冲突
- 同一文件重新导入时，通过 source 条件删除旧数据后重新生成 ID

---

## 命令行工具设计

```bash
python app/scripts/import_knowledge.py            # 增量同步
python app/scripts/import_knowledge.py --force     # 全量重建
python app/scripts/import_knowledge.py --reimport "关键词"   # 重新导入指定文件
python app/scripts/import_knowledge.py --reimport-failed     # 重试失败文件
python app/scripts/import_knowledge.py --status    # 查看状态
```

**设计亮点**：
- 幂等性：多次运行结果相同
- 可观测性：每个步骤都有日志和进度显示
- 灵活性：支持全量/增量/指定文件三种模式

---

## 完整数据流

```
用户放入 PDF → 扫描目录 → 状态检测（新增/更新/删除/无变化）
                              ↓
                新增/更新 → MinerU API 解析 → Markdown
                              ↓
                    load_and_split 切分 → 向量化 → ChromaDB
                              ↓
                    记录到 import_record.json
```

---

## 面试话术

> "我设计了一套知识库增量管理系统，核心思路是将文件同步类比为 Git 工作流。用户只需往目录放 PDF，脚本会自动检测新增、更新、删除三种变化，只处理变化的部分。通过文件修改时间对比实现自动更新检测，通过三层联动清理保证删除不留残余。整个流程保证幂等性，重复运行不会出错。"

---

## 技术关键词

- 增量同步、幂等性、文件修改时间检测
- MinerU 精准解析 API、通义千问 Embedding、ChromaDB
- 三层清理机制（MD + 向量 + 记录）
- Source 全局唯一性、完整相对路径
- 声明式文件管理、目录结构一致性
- LLM Fallback 兜底机制

(((
    . commit message 解释
"知识库一键导入工具与增量同步机制" 拆开看：

知识库一键导入工具 — import_knowledge.py 脚本，一条命令完成 PDF → MD → 向量的全流程

增量同步机制 — 脚本不只是"导入"，还能自动检测三种变化：

新增：data/raw/ 里多了 PDF → 自动导入
更新：PDF 被替换了（修改时间变了）→ 自动重新导入
删除：PDF 被删了 → 自动清理 MD 和向量数据
简单说就是：用户只管往目录里放/删 PDF，脚本自动保持知识库与目录同步，不用每次都全量重建。所以叫"增量同步"而不是"全量导入"。
)))