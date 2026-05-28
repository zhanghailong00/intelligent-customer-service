"""
知识库自动初始化模块

功能：
- 应用启动时自动检测文档变化
- 增量更新向量数据库（只处理新增/更新的文档）
- 清理已删除文档的向量数据

使用场景：
- Hugging Face Space 启动时自动初始化
- 本地开发时自动同步知识库

增量同步逻辑：
1. 扫描 data/raw/ 中的所有文档
2. 查找已删除的文件 → 清理 MD 和向量数据
3. 查找新增的文件 → 导入
4. 查找更新的文件 → 重新导入
5. 跳过未变化的文件
"""
import os
import sys

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.rag.imported_files import (
    find_deleted_files,
    find_new_files,
    find_updated_files,
    delete_file_record,
    get_import_stats,
    load_record
)
from app.rag.loader import load_and_split
from app.rag.vectorstore import add_documents


def init_knowledge_base():
    """
    初始化知识库（增量同步）

    启动时自动检测文档变化，只处理新增/更新的文档。
    """
    print("=" * 60)
    print("[Startup] 知识库初始化开始")
    print("=" * 60)

    # 检查 data/raw/ 目录
    raw_dir = os.path.join(PROJECT_ROOT, "data", "raw")
    if not os.path.exists(raw_dir):
        os.makedirs(raw_dir, exist_ok=True)
        print(f"[Startup] 已创建目录：{raw_dir}")
        print(f"[Startup] 请将文档放入此目录")
        return

    # 扫描所有文档文件
    doc_files = scan_document_files(raw_dir)
    print(f"[Startup] 扫描到 {len(doc_files)} 个文档文件")

    if not doc_files:
        print("[Startup] 没有找到文档文件，跳过初始化")
        return

    # 查找并清理已删除的文件
    cleanup_deleted_files()

    # 查找并处理新增和更新的文件
    processed_count = process_new_and_updated_files(doc_files)

    # 显示统计信息
    stats = get_import_stats()
    print(f"\n[Startup] 知识库初始化完成")
    print(f"  已导入文件：{stats['total_files']} 个")
    print(f"  总 chunk 数：{stats['total_chunks']} 个")
    print("=" * 60)


def scan_document_files(raw_dir: str) -> list:
    """
    扫描 data/raw/ 目录中的所有文档文件

    Args:
        raw_dir: 原始文档目录

    Returns:
        文档文件路径列表（绝对路径）
    """
    doc_files = []
    for root, dirs, files in os.walk(raw_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                doc_files.append(os.path.join(root, file))
    return doc_files


def cleanup_deleted_files():
    """
    清理已删除文件的向量数据

    查找 JSON 有记录但文件不存在的情况，清理对应的向量数据。
    使用 filename 字段（相对路径）来检查文件是否存在。
    """
    from app.rag.imported_files import load_record

    record = load_record()
    raw_dir = os.path.join(PROJECT_ROOT, "data", "raw")

    deleted_files = []
    for f in record.get("imported_files", []):
        filename = f.get("filename", "")
        if not filename:
            continue

        # 构建完整的文件路径
        file_path = os.path.join(raw_dir, filename.replace("\\", os.sep))

        # 检查文件是否存在
        if not os.path.exists(file_path):
            deleted_files.append(f)

    if not deleted_files:
        return

    print(f"\n[Startup] 检测到 {len(deleted_files)} 个已删除的文件：")
    for f in deleted_files:
        filename = f['filename']
        print(f"  - {filename}")
        delete_file_record(filename)
        print(f"    [清理] 已删除向量数据")


def process_new_and_updated_files(doc_files: list) -> int:
    """
    处理新增和更新的文件

    Args:
        doc_files: 文档文件列表

    Returns:
        处理的文件数量
    """
    from app.rag.imported_files import is_imported, is_file_updated, get_imported_filenames

    processed_count = 0
    raw_dir = os.path.join(PROJECT_ROOT, "data", "raw")

    # 获取已导入文件名集合（用于快速查找）
    imported_filenames = get_imported_filenames()

    for doc_path in doc_files:
        # 获取相对路径（使用反斜杠，与 import_record.json 一致）
        relative_path = os.path.relpath(doc_path, raw_dir).replace("/", "\\")

        # 检查是否需要处理
        if relative_path in imported_filenames:
            # 文件已导入，检查是否更新
            if is_file_updated(relative_path, doc_path):
                print(f"\n[Startup] [更新] {relative_path}")
                if process_single_file(doc_path, relative_path):
                    processed_count += 1
            # else: 跳过未变化的文件
        else:
            # 新文件
            print(f"\n[Startup] [新增] {relative_path}")
            if process_single_file(doc_path, relative_path):
                processed_count += 1

    return processed_count


def process_single_file(doc_path: str, relative_path: str) -> bool:
    """
    处理单个文档文件

    流程：
    - PDF 文件：MinerU API → Markdown → 切分 → 向量化
    - Markdown 文件：直接切分 → 向量化

    Args:
        doc_path: 文档文件路径
        relative_path: 相对路径

    Returns:
        是否处理成功
    """
    try:
        from app.rag.imported_files import mark_imported

        # 根据文件类型选择处理方式
        if doc_path.lower().endswith('.pdf'):
            # PDF 文件：先用 MinerU 转成 Markdown
            md_path = convert_pdf_to_markdown(doc_path)
            if not md_path:
                mark_imported(relative_path, chunks_count=0, status="failed", file_path=doc_path)
                return False
            process_path = md_path
        else:
            # Markdown/文本文件：直接处理
            process_path = doc_path

        # 加载并切分文档
        print(f"  加载并切分文档...")
        chunks = load_and_split(process_path)
        print(f"  切分为 {len(chunks)} 个 chunk")

        if not chunks:
            print(f"  [警告] 文档切分结果为空")
            mark_imported(relative_path, chunks_count=0, status="failed", file_path=doc_path)
            return False

        # 向量化并存储
        print(f"  调用 Embedding API 向量化...")
        count = add_documents(chunks)
        print(f"  [成功] 存储完成，共 {count} 个文档")

        # 记录导入成功
        mark_imported(relative_path, chunks_count=count, status="success", file_path=doc_path)
        return True

    except Exception as e:
        print(f"  [错误] 处理失败：{type(e).__name__}: {e}")
        from app.rag.imported_files import mark_imported
        mark_imported(relative_path, chunks_count=0, status="failed", file_path=doc_path)
        return False


def convert_pdf_to_markdown(pdf_path: str) -> str:
    """
    使用 MinerU API 将 PDF 转换为 Markdown

    Args:
        pdf_path: PDF 文件路径

    Returns:
        生成的 Markdown 文件路径，失败返回空字符串
    """
    import time
    import requests
    import zipfile
    import io
    from dotenv import load_dotenv

    # 加载环境变量
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

    mineru_token = os.getenv("MINERU_TOKEN")
    if not mineru_token:
        print(f"  [错误] 未配置 MINERU_TOKEN")
        return ""

    filename = os.path.basename(pdf_path)
    pdf_name = os.path.splitext(filename)[0]
    processed_dir = os.path.join(PROJECT_ROOT, "data", "processed")

    print(f"  调用 MinerU API 解析：{filename}")

    # 检查是否已有解析结果
    md_path = os.path.join(processed_dir, pdf_name, f"{pdf_name}.md")
    if os.path.exists(md_path):
        print(f"  [跳过] 已有解析结果：{md_path}")
        return md_path

    try:
        from app.scripts.import_knowledge import (
            get_upload_urls, upload_file, poll_result, download_and_extract
        )

        # 1. 获取上传链接
        result = get_upload_urls(filename)
        if not result:
            return ""

        batch_id, file_url = result

        # 2. 上传文件
        if not upload_file(pdf_path, file_url):
            return ""

        # 3. 轮询结果
        zip_url = poll_result(batch_id)
        if not zip_url:
            return ""

        # 4. 下载并解压
        output_dir = os.path.join(processed_dir, pdf_name)
        os.makedirs(output_dir, exist_ok=True)

        if not download_and_extract(zip_url, output_dir, pdf_name):
            return ""

        # 返回 Markdown 文件路径
        if os.path.exists(md_path):
            print(f"  [成功] 解析完成：{md_path}")
            return md_path
        else:
            print(f"  [错误] 未找到生成的 Markdown 文件")
            return ""

    except Exception as e:
        print(f"  [错误] MinerU 解析失败：{type(e).__name__}: {e}")
        return ""


if __name__ == "__main__":
    # 可以单独运行测试
    init_knowledge_base()
