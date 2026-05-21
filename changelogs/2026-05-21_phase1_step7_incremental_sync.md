# 改动摘要：Phase 1 收尾 - 知识库增量同步完善

**日期**：2026-05-21
**操作人**：Claude
**任务**：完善一键导入工具的增量同步逻辑，支持新增/更新/删除检测

---

## 改动文件列表

| 文件 | 说明 |
|---|---|
| `app/rag/imported_files.py` | 修复路径匹配、mtime 检测、文件查找逻辑、删除向量数据逻辑 |
| `app/rag/loader.py` | 修复 source 格式，使用完整相对路径确保全局唯一 |
| `app/rag/vectorstore.py` | 更新注释，说明新 ID 格式 |
| `app/scripts/import_knowledge.py` | 增加删除检测、修复路径分隔符、状态显示优化 |
| `interview_highlights/02_knowledge_base_management.md` | 新增面试亮点文档 |
| `changelogs/2026-05-21_phase1_step7_incremental_sync.md` | 本改动摘要 |

---

## 每个文件的改动详情

### app/rag/imported_files.py（修改）

**修复 1：路径分隔符统一**

`get_relative_path()` 返回的路径统一使用反斜杠，与 Windows 和 `import_record.json` 保持一致。

**修复 2：`is_file_updated()` 处理旧记录**

旧的导入记录没有 `file_mtime` 字段，导致比较时空字符串总是被判定为"已更新"。修复：当记录中没有 `file_mtime` 时，自动补全当前修改时间，视为未更新。

**修复 3：`find_new_files()` 路径匹配**

使用完整的相对路径（包含子目录）进行匹配，而不是仅用文件名。

**修复 4：`delete_vector_data()` source 格式对齐**

修改为与 `loader.py` 一致的 source 格式：`子目录\文件名\文件名.md`

### app/rag/loader.py（修改）

**修复：source 格式全局唯一**

`load_and_split()` 中 source 改为相对于 `data/processed/` 的完整路径（含子目录），确保不同子目录下同名文件不会冲突。

例如：`实验箱前期准备工作\01-实验前准备\01-实验前准备.md`

### app/rag/vectorstore.py（修改）

**更新注释**：说明新 ID 格式包含完整路径。

### app/scripts/import_knowledge.py（修改）

**新增：删除检测**

在 main() 函数中增加删除检测逻辑，扫描 JSON 记录，如果 PDF 文件不存在则清理 MD 和向量数据。

**修复：路径分隔符**

`get_relative_path()` 统一使用反斜杠路径。

**优化：状态显示**

`show_status()` 增加待处理文件统计，显示新增/更新/删除的数量。

---

## 测试验证

| 测试场景 | 预期结果 | 实际结果 |
|---|---|---|
| 已导入文件再次运行 | 跳过 | ✓ 跳过 |
| `--status` 查看状态 | 正确显示文件列表 | ✓ 正常 |
| 文件未变化时运行 | 无需操作 | ✓ 正常 |
| 删除检测 | 无已删除文件 | ✓ 正常 |
| GBK 编码兼容 | 不报错 | ✓ 正常 |
| source 全局唯一 | 不同子目录同名文件不冲突 | ✓ 已修复 |
