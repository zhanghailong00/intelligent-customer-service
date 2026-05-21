"""
导入记录模块

功能：
- 记录已导入的文件信息，避免重复导入
- 记录文件修改时间，自动检测文件更新
- 支持查询导入状态和统计信息
- 数据持久化到 JSON 文件
- 自动检测已删除的文件，清理 MD 和向量数据

数据存储位置：data/import_record.json

文件名格式：使用相对于 data/raw/ 的完整路径（含子目录），
例如 "实验箱前期准备工作\\01-实验前准备和结束收纳.pdf"

使用示例：
    from app.rag.imported_files import is_imported, mark_imported, get_import_stats, is_file_updated

    # 检查文件是否已导入
    if not is_imported("实验箱前期准备工作\\01-实验前准备和结束收纳.pdf"):
        # 执行导入...
        mark_imported("实验箱前期准备工作\\01-实验前准备和结束收纳.pdf", chunks_count=3,
                      file_path="data/raw/实验箱前期准备工作\\01-实验前准备和结束收纳.pdf")

    # 检查文件是否已更新
    if is_file_updated("实验箱前期准备工作\\01-实验前准备和结束收纳.pdf",
                       "data/raw/实验箱前期准备工作\\01-实验前准备和结束收纳.pdf"):
        print("文件已更新，需要重新导入")

    # 查找已删除的文件
    from app.rag.imported_files import find_deleted_files, delete_file_record
    deleted = find_deleted_files()
    for f in deleted:
        delete_file_record(f['filename'])  # 自动清理 MD 和向量数据

    # 获取统计信息
    stats = get_import_stats()
    print(f"已导入 {stats['total_files']} 个文件，共 {stats['total_chunks']} 个 chunk")
"""
import os
import json
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Set

# 导入记录文件路径（项目根目录/data/import_record.json）
IMPORT_RECORD_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "import_record.json"
)

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 数据目录
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")


def load_record() -> Dict:
    """
    加载导入记录

    从 JSON 文件读取导入记录，如果文件不存在则返回空记录。

    Returns:
        导入记录字典，格式：
        {
            "imported_files": [
                {
                    "filename": "xxx.pdf",
                    "relative_path": "子目录/xxx.pdf",
                    "file_path": "data/raw/子目录/xxx.pdf",
                    "file_mtime": "2026-05-21T10:30:00",
                    "chunks_count": 3,
                    "status": "success",
                    "imported_at": "2026-05-21T10:30:00"
                }
            ]
        }
    """
    if os.path.exists(IMPORT_RECORD_FILE):
        with open(IMPORT_RECORD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"imported_files": []}


def save_record(record: Dict):
    """
    保存导入记录

    将导入记录写入 JSON 文件。

    Args:
        record: 导入记录字典
    """
    # 确保 data 目录存在
    os.makedirs(os.path.dirname(IMPORT_RECORD_FILE), exist_ok=True)

    # 写入 JSON 文件，ensure_ascii=False 支持中文
    with open(IMPORT_RECORD_FILE, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def get_file_mtime(file_path: str) -> Optional[str]:
    """
    获取文件的修改时间

    Args:
        file_path: 文件的绝对路径或相对路径

    Returns:
        文件修改时间的 ISO 格式字符串，文件不存在返回 None

    使用示例：
        mtime = get_file_mtime("data/raw/02-实验环境的搭建.pdf")
        print(f"文件修改时间：{mtime}")
    """
    if not os.path.exists(file_path):
        return None

    # 获取文件修改时间戳
    mtime_timestamp = os.path.getmtime(file_path)

    # 转换为 ISO 格式字符串
    mtime_datetime = datetime.fromtimestamp(mtime_timestamp)
    return mtime_datetime.isoformat()


def is_file_updated(filename: str, file_path: str) -> bool:
    """
    检查文件是否已更新（修改时间是否变新）

    用于自动检测 PDF 文件是否被更新，决定是否需要重新导入。

    Args:
        filename: 文件名（相对路径，用于记录中查找）
        file_path: 文件的绝对路径或相对路径（用于获取修改时间）

    Returns:
        True 表示文件已更新，False 表示未更新或文件不存在

    使用示例：
        if is_file_updated("01-实验前准备.pdf", "data/raw/实验箱/01-实验前准备.pdf"):
            print("文件已更新，需要重新导入")
    """
    # 获取文件当前修改时间
    current_mtime = get_file_mtime(file_path)
    if current_mtime is None:
        return False

    # 查找导入记录
    record = load_record()
    for f in record["imported_files"]:
        if f["filename"] == filename:
            # 获取记录中的修改时间
            record_mtime = f.get("file_mtime", "")

            # 如果记录中没有修改时间，说明是旧记录，自动补全并视为未更新
            if not record_mtime:
                f["file_mtime"] = current_mtime
                save_record(record)
                return False

            # 比较：如果当前修改时间 > 记录时间，说明文件已更新
            if current_mtime > record_mtime:
                return True
            return False

    # 文件未导入过，不算"更新"
    return False


def is_imported(filename: str) -> bool:
    """
    检查文件是否已导入

    Args:
        filename: 文件名（如 "02-实验环境的搭建.pdf"）

    Returns:
        True 表示已导入，False 表示未导入

    使用示例：
        if not is_imported("新文件.pdf"):
            print("可以导入")
    """
    record = load_record()
    imported_files = [f["filename"] for f in record["imported_files"]]
    return filename in imported_files


def mark_imported(filename: str, chunks_count: int, status: str = "success",
                  file_path: Optional[str] = None, relative_path: Optional[str] = None):
    """
    标记文件已导入

    记录文件的导入状态和修改时间，如果文件已存在则更新。

    Args:
        filename: 文件名（不含路径，如 "02-实验环境的搭建.pdf"）
        chunks_count: 切分的 chunk 数量
        status: 导入状态
            - "success": 导入成功
            - "failed": 导入失败
            - "partial": 部分成功
        file_path: 文件的完整路径（用于获取修改时间）
        relative_path: 文件的相对路径（用于记录目录结构）

    使用示例：
        mark_imported("新文件.pdf", chunks_count=5, file_path="data/raw/子目录/新文件.pdf",
                      relative_path="子目录/新文件.pdf")
    """
    record = load_record()

    # 获取文件修改时间
    file_mtime = ""
    if file_path:
        file_mtime = get_file_mtime(file_path) or ""

    # 检查是否已存在，如果存在则更新
    for f in record["imported_files"]:
        if f["filename"] == filename:
            f["chunks_count"] = chunks_count
            f["status"] = status
            f["file_mtime"] = file_mtime
            f["file_path"] = file_path or f.get("file_path", "")
            f["relative_path"] = relative_path or f.get("relative_path", "")
            f["updated_at"] = datetime.now().isoformat()
            save_record(record)
            return

    # 不存在则添加新记录
    record["imported_files"].append({
        "filename": filename,
        "relative_path": relative_path or "",
        "file_path": file_path or "",
        "file_mtime": file_mtime,
        "chunks_count": chunks_count,
        "status": status,
        "imported_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    })

    save_record(record)


def get_imported_files() -> List[Dict]:
    """
    获取已导入文件列表

    Returns:
        已导入文件列表，每个元素包含：
        - filename: 文件名
        - relative_path: 相对路径
        - file_mtime: 文件修改时间
        - chunks_count: chunk 数量
        - status: 导入状态
        - imported_at: 导入时间
    """
    record = load_record()
    return record.get("imported_files", [])


def get_imported_filenames() -> Set[str]:
    """
    获取已导入文件名集合

    Returns:
        已导入文件名集合
    """
    record = load_record()
    return {f["filename"] for f in record["imported_files"]}


def get_import_stats() -> Dict:
    """
    获取导入统计信息

    Returns:
        统计信息字典：
        - total_files: 总文件数
        - success_files: 成功数
        - failed_files: 失败数
        - total_chunks: 总 chunk 数

    使用示例：
        stats = get_import_stats()
        print(f"已导入 {stats['total_files']} 个文件")
    """
    record = load_record()
    files = record.get("imported_files", [])

    # 统计各项数据
    total_chunks = sum(f.get("chunks_count", 0) for f in files)
    success_count = sum(1 for f in files if f.get("status") == "success")
    failed_count = sum(1 for f in files if f.get("status") == "failed")

    return {
        "total_files": len(files),
        "success_files": success_count,
        "failed_files": failed_count,
        "total_chunks": total_chunks
    }


def clear_record():
    """
    清空导入记录

    注意：这不会删除已导入的向量数据，只是清空记录。
    """
    save_record({"imported_files": []})
    print("导入记录已清空")


def remove_record(filename: str) -> bool:
    """
    删除指定文件的导入记录

    用于重新导入特定文件。

    Args:
        filename: 文件名（相对路径）

    Returns:
        是否成功删除

    使用示例：
        remove_record("实验箱前期准备工作\\01-实验前准备和结束收纳.pdf")
    """
    record = load_record()
    original_count = len(record["imported_files"])

    # 过滤掉指定文件
    record["imported_files"] = [
        f for f in record["imported_files"]
        if f["filename"] != filename
    ]

    new_count = len(record["imported_files"])

    if original_count > new_count:
        save_record(record)
        return True
    return False


def remove_records_by_keyword(keyword: str) -> int:
    """
    根据关键词删除导入记录

    支持模糊匹配，用于批量重新导入。

    Args:
        keyword: 搜索关键词（支持部分匹配）

    Returns:
        删除的记录数量

    使用示例：
        # 删除所有包含 "01" 的记录
        count = remove_records_by_keyword("01")

        # 删除特定目录下的记录
        count = remove_records_by_keyword("实验箱前期准备工作")
    """
    record = load_record()
    original_count = len(record["imported_files"])

    # 过滤掉包含关键词的文件
    record["imported_files"] = [
        f for f in record["imported_files"]
        if keyword not in f["filename"]
    ]

    new_count = len(record["imported_files"])
    deleted_count = original_count - new_count

    if deleted_count > 0:
        save_record(record)

    return deleted_count


def find_imported_file(keyword: str) -> List[Dict]:
    """
    根据关键词查找已导入的文件

    Args:
        keyword: 搜索关键词

    Returns:
        匹配的文件列表

    使用示例：
        files = find_imported_file("01")
        for f in files:
            print(f["filename"])
    """
    record = load_record()
    return [
        f for f in record["imported_files"]
        if keyword in f["filename"]
    ]


def delete_file_record(filename: str) -> bool:
    """
    删除文件记录及其对应的 MD 和向量数据

    用于删除已导入的文件。

    Args:
        filename: 文件名（相对路径，如 "子目录/xxx.pdf"）

    Returns:
        是否成功删除

    使用示例：
        delete_file_record("实验箱/01-实验前准备.pdf")
    """
    record = load_record()

    # 查找要删除的记录
    target_record = None
    for f in record["imported_files"]:
        if f["filename"] == filename:
            target_record = f
            break

    if not target_record:
        return False

    # 1. 删除 MD 文件和目录
    md_deleted = delete_md_files(target_record)

    # 2. 删除向量数据
    vector_deleted = delete_vector_data(target_record)

    # 3. 删除记录
    record["imported_files"] = [
        f for f in record["imported_files"]
        if f["filename"] != filename
    ]
    save_record(record)

    return True


def delete_md_files(record: Dict) -> bool:
    """
    删除文件对应的 MD 文件和目录

    根据记录中的相对路径，删除 processed 目录下对应的 MD 文件。

    Args:
        record: 文件导入记录

    Returns:
        是否成功删除
    """
    relative_path = record.get("relative_path", "")
    if not relative_path:
        return False

    # 构建 MD 目录路径
    # 例如：relative_path = "实验箱/01-实验前准备.pdf"
    # MD 目录 = data/processed/实验箱/01-实验前准备/
    pdf_name = os.path.splitext(os.path.basename(relative_path))[0]
    sub_dir = os.path.dirname(relative_path)

    if sub_dir:
        md_dir = os.path.join(PROCESSED_DIR, sub_dir, pdf_name)
    else:
        md_dir = os.path.join(PROCESSED_DIR, pdf_name)

    # 删除整个目录
    if os.path.exists(md_dir):
        try:
            shutil.rmtree(md_dir)
            print(f"  [删除] MD 目录：{md_dir}")
            return True
        except Exception as e:
            print(f"  [错误] 删除 MD 目录失败：{type(e).__name__}: {e}")
            return False

    return False


def delete_vector_data(record: Dict) -> bool:
    """
    删除文件对应的向量数据

    根据记录中的 source 字段，删除 ChromaDB 中对应的向量。

    Args:
        record: 文件导入记录

    Returns:
        是否成功删除
    """
    try:
        from app.rag.vectorstore import get_vectorstore

        filename = record.get("filename", "")
        if not filename:
            return False

        # 构建 source 名称（与 loader.py 中 load_and_split 一致）
        # source = 相对路径，如 "实验箱前期准备工作\01-实验前准备和结束收纳\01-实验前准备和结束收纳.md"
        pdf_name_no_ext = os.path.splitext(os.path.basename(filename))[0]
        sub_dir = os.path.dirname(filename)
        if sub_dir:
            source = f"{sub_dir}\\{pdf_name_no_ext}\\{pdf_name_no_ext}.md"
        else:
            source = f"{pdf_name_no_ext}\\{pdf_name_no_ext}.md"

        # 获取向量数据库
        client, collection = get_vectorstore()

        # 删除该 source 的所有向量
        initial_count = collection.count()
        collection.delete(where={"source": source})
        final_count = collection.count()

        deleted_count = initial_count - final_count
        if deleted_count > 0:
            print(f"  [删除] 向量数据：{deleted_count} 个 chunk (source={source})")
            return True

        return False

    except Exception as e:
        print(f"  [错误] 删除向量数据失败：{type(e).__name__}: {e}")
        return False


def find_deleted_files() -> List[Dict]:
    """
    查找已删除的文件（JSON 有记录，但 PDF 不存在）

    用于检测用户手动删除的 PDF 文件。

    Returns:
        需要删除的文件记录列表

    使用示例：
        deleted = find_deleted_files()
        for f in deleted:
            print(f"需要删除：{f['filename']}")
    """
    record = load_record()
    deleted_files = []

    for f in record["imported_files"]:
        file_path = f.get("file_path", "")
        if file_path and not os.path.exists(file_path):
            deleted_files.append(f)

    return deleted_files


def find_orphan_md_dirs() -> List[str]:
    """
    查找孤立的 MD 目录（processed 中有 MD 目录，但 JSON 中无对应记录）

    用于检测 --force 清空记录后残留的 MD 文件。
    例如：用户删除了 PDF，然后运行 --force，JSON 记录被清空，
    但 processed 下的 MD 目录还在。

    Returns:
        需要清理的 MD 目录路径列表

    使用示例：
        orphans = find_orphan_md_dirs()
        for d in orphans:
            print(f"孤立目录：{d}")
    """
    record = load_record()
    imported_filenames = {f["filename"] for f in record["imported_files"]}
    orphan_dirs = []

    # 遍历 processed 目录下的所有子目录
    if not os.path.exists(PROCESSED_DIR):
        return orphan_dirs

    for item in os.listdir(PROCESSED_DIR):
        item_path = os.path.join(PROCESSED_DIR, item)
        if not os.path.isdir(item_path):
            continue

        # 检查该目录下是否有 .md 文件
        has_md = any(f.endswith(".md") for f in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, f)))
        if not has_md:
            continue

        # 尝试匹配 JSON 记录
        # processed 目录结构：data/processed/{子目录}/{pdf_name}/{pdf_name}.md
        # 或简单结构：data/processed/{pdf_name}/{pdf_name}.md
        # 对应的 filename 格式：{子目录}\{pdf_name}.pdf 或 {pdf_name}.pdf

        # 构建可能的 filename 进行匹配
        matched = False
        for filename in imported_filenames:
            filename_no_ext = os.path.splitext(os.path.basename(filename))[0]
            if filename_no_ext == item:
                matched = True
                break

        if not matched:
            orphan_dirs.append(item_path)

    return orphan_dirs


def cleanup_orphan_md_dirs(orphan_dirs: List[str]) -> int:
    """
    清理孤立的 MD 目录

    Args:
        orphan_dirs: 需要清理的目录列表

    Returns:
        清理的目录数量
    """
    cleaned = 0
    for dir_path in orphan_dirs:
        try:
            # 同时清理向量数据
            dir_name = os.path.basename(dir_path)
            # 尝试删除该目录对应的向量数据
            _cleanup_vector_for_md_dir(dir_name)

            # 删除 MD 目录
            shutil.rmtree(dir_path)
            print(f"  [清理] 删除孤立目录：{dir_path}")
            cleaned += 1
        except Exception as e:
            print(f"  [错误] 清理目录失败：{type(e).__name__}: {e}")

    return cleaned


def _cleanup_vector_for_md_dir(dir_name: str):
    """
    根据 processed 目录名清理对应的向量数据

    Args:
        dir_name: processed 下的目录名（不含路径）
    """
    try:
        from app.rag.vectorstore import get_vectorstore
        client, collection = get_vectorstore()

        # 尝试匹配 source：{dir_name}\{dir_name}.md
        source = f"{dir_name}\\{dir_name}.md"
        initial_count = collection.count()
        collection.delete(where={"source": source})
        deleted_count = initial_count - collection.count()

        if deleted_count > 0:
            print(f"  [清理] 删除向量数据：{deleted_count} 个 chunk (source={source})")
    except Exception:
        pass


def find_new_files(pdf_files: List[str]) -> List[str]:
    """
    查找新增的文件（PDF 存在，但 JSON 没记录）

    Args:
        pdf_files: 当前目录中的 PDF 文件路径列表

    Returns:
        新增的 PDF 文件路径列表

    使用示例：
        pdf_files = scan_pdf_files()
        new_files = find_new_files(pdf_files)
    """
    imported_filenames = get_imported_filenames()
    new_files = []

    for pdf_path in pdf_files:
        # 使用完整的相对路径进行匹配（包含子目录）
        # 例如："实验箱前期准备工作\\01-实验前准备和结束收纳.pdf"
        filename = os.path.relpath(pdf_path, RAW_DIR).replace("/", "\\")
        if filename not in imported_filenames:
            new_files.append(pdf_path)

    return new_files


def find_updated_files(pdf_files: List[str]) -> List[str]:
    """
    查找更新的文件（JSON 有记录，但 PDF 修改时间更新）

    Args:
        pdf_files: 当前目录中的 PDF 文件路径列表

    Returns:
        更新的 PDF 文件路径列表

    使用示例：
        pdf_files = scan_pdf_files()
        updated_files = find_updated_files(pdf_files)
    """
    updated_files = []

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        if is_imported(filename) and is_file_updated(filename, pdf_path):
            updated_files.append(pdf_path)

    return updated_files


def find_unchanged_files(pdf_files: List[str]) -> List[str]:
    """
    查找未变化的文件（JSON 有记录，PDF 也在，时间一样）

    Args:
        pdf_files: 当前目录中的 PDF 文件路径列表

    Returns:
        未变化的 PDF 文件路径列表

    使用示例：
        pdf_files = scan_pdf_files()
        unchanged_files = find_unchanged_files(pdf_files)
    """
    unchanged_files = []

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        if is_imported(filename) and not is_file_updated(filename, pdf_path):
            unchanged_files.append(pdf_path)

    return unchanged_files
