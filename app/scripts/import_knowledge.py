"""
一键导入知识库脚本

功能：
- 递归扫描 data/raw/ 目录及其子目录下的 PDF 文件（支持无限层级子目录）
- 调用 MinerU 精准解析 API 将 PDF 转换为 Markdown
- 调用向量化存储到 ChromaDB
- 记录导入状态，避免重复导入
- 自动检测文件更新（对比 PDF 修改时间与 JSON 记录时间）
- 自动检测文件删除（PDF 不存在时清理 MD 和向量数据）
- 支持强制重新导入和指定文件重新导入

增量同步逻辑：
    - 新增：PDF 存在，JSON 无记录 → 解析 → 向量化 → 记录
    - 更新：JSON 有记录，PDF 修改时间 > JSON 记录时间 → 删旧数据 → 重新导入
    - 删除：JSON 有记录，PDF 不存在 → 清理 MD + 向量 + 记录
    - 无变化：JSON 有记录，PDF 在，时间相同 → 跳过

使用方式：
    # 正常导入（跳过已导入的文件，自动检测更新和删除）
    python app/scripts/import_knowledge.py

    # 强制重新导入所有文件（清空向量数据库后重建）
    python app/scripts/import_knowledge.py --force

    # 重新导入指定文件（支持模糊匹配）
    python app/scripts/import_knowledge.py --reimport "01-实验前准备"

    # 重新导入失败的文件
    python app/scripts/import_knowledge.py --reimport-failed

    # 查看导入状态
    python app/scripts/import_knowledge.py --status

流程：
    1. 递归扫描 data/raw/ 目录
    2. 检测已删除的文件（PDF 不存在，但 JSON 有记录）→ 清理 MD 和向量数据
    3. 检测新增和更新的文件
    4. 对新 PDF 或更新的 PDF 调用 MinerU API 解析 → Markdown
    5. 对 Markdown 运行向量化存储
    6. 记录导入状态和文件修改时间

目录结构要求：
    data/raw/ 和 data/processed/ 保持一致的子目录结构，
    例如 data/raw/实验箱/01-实验前准备.pdf
    对应 data/processed/实验箱/01-实验前准备/01-实验前准备.md

注意：
    - 运行前请确保 .env 中配置了 MINERU_TOKEN
    - MinerU 使用在线 API，需要网络连接
    - 不要开启 VPN
"""
import os
import sys
import time
import argparse
import requests
import zipfile
import io
from typing import Optional, Tuple, List
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# 加载环境变量
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# 数据目录
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

# MinerU API 配置
MINERU_BASE_URL = "https://mineru.net/api/v4"
MINERU_TOKEN = os.getenv("MINERU_TOKEN")

# 导入相关模块
from app.rag.imported_files import is_imported, mark_imported, get_import_stats, is_file_updated
from app.rag.loader import load_and_split
from app.rag.vectorstore import add_documents


def scan_pdf_files() -> List[str]:
    """
    递归扫描 data/raw/ 目录及其所有子目录下的 PDF 文件

    支持多层目录结构，例如：
        data/raw/
        ├── 手册1.pdf
        ├── 农业设备/
        │   ├── 农业手册1.pdf
        │   └── 农业手册2.pdf
        └── 工业设备/
            └── 工业手册.pdf

    Returns:
        PDF 文件路径列表（绝对路径）
    """
    if not os.path.exists(RAW_DIR):
        os.makedirs(RAW_DIR)
        print(f"[提示] 已创建目录：{RAW_DIR}")
        print(f"[提示] 请将 PDF 文件放入此目录，然后重新运行脚本。")
        return []

    # 递归扫描所有 PDF 文件
    pdf_files = []
    for root, dirs, files in os.walk(RAW_DIR):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))

    return pdf_files


def get_relative_path(pdf_path: str) -> str:
    """
    获取相对于 data/raw/ 目录的相对路径

    用于记录导入状态，避免不同目录下的同名文件冲突。

    Args:
        pdf_path: PDF 文件的绝对路径

    Returns:
        相对路径，例如 "农业设备/农业手册1.pdf"

    注意：路径分隔符统一使用反斜杠，与 import_record.json 保持一致
    """
    # 获取相对路径
    rel_path = os.path.relpath(pdf_path, RAW_DIR)
    # 统一使用反斜杠，与 Windows 和 import_record.json 保持一致
    return rel_path.replace("/", "\\")


def get_upload_urls(file_name: str) -> Optional[Tuple[str, str]]:
    """
    获取 MinerU 文件上传签名 URL

    Args:
        file_name: 文件名

    Returns:
        (batch_id, file_url) 元组，失败返回 None
    """
    url = f"{MINERU_BASE_URL}/file-urls/batch"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MINERU_TOKEN}"
    }
    data = {
        "files": [{"name": file_name}],
        "model_version": "vlm"  # 使用 vlm 模型，精度更高
    }

    try:
        resp = requests.post(url, headers=headers, json=data)
        result = resp.json()

        if result["code"] != 0:
            print(f"  [错误] 获取上传链接失败：{result['msg']}")
            return None

        batch_id = result["data"]["batch_id"]
        file_url = result["data"]["file_urls"][0]
        return batch_id, file_url
    except Exception as e:
        print(f"  [错误] 获取上传链接异常：{type(e).__name__}: {e}")
        return None


def upload_file(file_path: str, file_url: str) -> bool:
    """
    上传文件到 MinerU OSS

    Args:
        file_path: 本地文件路径
        file_url: 上传 URL

    Returns:
        是否成功
    """
    try:
        with open(file_path, "rb") as f:
            resp = requests.put(file_url, data=f)

        if resp.status_code in (200, 201):
            return True
        else:
            print(f"  [错误] 文件上传失败，HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"  [错误] 文件上传异常：{type(e).__name__}: {e}")
        return False


def poll_result(batch_id: str, timeout: int = 300, interval: int = 3) -> Optional[str]:
    """
    轮询查询 MinerU 解析结果

    Args:
        batch_id: 批量任务 ID
        timeout: 超时时间（秒）
        interval: 轮询间隔（秒）

    Returns:
        ZIP 下载链接，失败返回 None
    """
    url = f"{MINERU_BASE_URL}/extract-results/batch/{batch_id}"
    headers = {"Authorization": f"Bearer {MINERU_TOKEN}"}
    start = time.time()

    while time.time() - start < timeout:
        try:
            resp = requests.get(url, headers=headers)
            result = resp.json()

            if result["code"] != 0:
                print(f"  [错误] 查询失败：{result['msg']}")
                return None

            extract_result = result["data"]["extract_result"][0]
            state = extract_result["state"]
            elapsed = int(time.time() - start)

            if state == "done":
                zip_url = extract_result["full_zip_url"]
                print(f"  [{elapsed}s] 解析完成")
                return zip_url

            if state == "failed":
                err_msg = extract_result.get("err_msg", "未知错误")
                print(f"  [错误] [{elapsed}s] 解析失败：{err_msg}")
                return None

            # 显示进度
            progress = extract_result.get("extract_progress", {})
            if progress:
                extracted = progress.get("extracted_pages", 0)
                total = progress.get("total_pages", 0)
                print(f"  [{elapsed}s] {state} ({extracted}/{total} 页)...")
            else:
                print(f"  [{elapsed}s] {state}...")

        except Exception as e:
            print(f"  [警告] 查询异常：{type(e).__name__}: {e}")

        time.sleep(interval)

    print(f"  [错误] 轮询超时 ({timeout}s)")
    return None


def download_and_extract(zip_url: str, output_dir: str, pdf_name: str) -> bool:
    """
    下载并解压 ZIP 文件

    Args:
        zip_url: ZIP 下载链接
        output_dir: 输出目录
        pdf_name: 原始 PDF 文件名（不含扩展名）

    Returns:
        是否成功
    """
    try:
        # 如果目标目录已存在，先清理（支持重复导入）
        if os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)

        print("  下载 ZIP 文件...")
        resp = requests.get(zip_url)

        if resp.status_code != 200:
            print(f"  [错误] 下载失败，HTTP {resp.status_code}")
            return False

        # 解压 ZIP
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            zf.extractall(output_dir)
            file_list = zf.namelist()
            print(f"  解压完成，共 {len(file_list)} 个文件")

            # 清理冗余文件
            cleanup_unnecessary_files(output_dir, file_list)

            # 重命名 full.md 为与 PDF 文件名相同
            rename_markdown(output_dir, pdf_name)

            return True

    except Exception as e:
        print(f"  [错误] 下载解压异常：{type(e).__name__}: {e}")
        return False


def cleanup_unnecessary_files(output_dir: str, file_list: list):
    """
    清理解析结果中的冗余文件

    只保留：
    - full.md（Markdown 主文件）
    - images/ 目录（图片文件）

    删除：
    - *.json（布局信息、内容列表）
    - *_origin.pdf（原始 PDF 副本）
    """
    deleted_count = 0
    for file_name in file_list:
        file_path = os.path.join(output_dir, file_name)

        # 跳过目录
        if os.path.isdir(file_path):
            continue

        # 判断是否需要删除
        should_delete = False

        # 删除 JSON 文件
        if file_name.endswith(".json"):
            should_delete = True

        # 删除原始 PDF
        if file_name.endswith("_origin.pdf"):
            should_delete = True

        if should_delete and os.path.exists(file_path):
            os.remove(file_path)
            deleted_count += 1

    if deleted_count > 0:
        print(f"  清理完成，删除了 {deleted_count} 个冗余文件")


def rename_markdown(output_dir: str, pdf_name: str):
    """
    重命名 full.md 为与 PDF 文件名相同

    Args:
        output_dir: 输出目录
        pdf_name: PDF 文件名（不含扩展名）
    """
    old_path = os.path.join(output_dir, "full.md")
    new_path = os.path.join(output_dir, f"{pdf_name}.md")

    if os.path.exists(old_path):
        # 如果目标文件已存在，先删除
        if os.path.exists(new_path):
            os.remove(new_path)
        os.rename(old_path, new_path)
        print(f"  重命名：full.md -> {pdf_name}.md")


def run_mineru_parse(pdf_path: str) -> str:
    """
    调用 MinerU API 解析 PDF 为 Markdown

    完整流程：获取上传链接 → 上传文件 → 轮询结果 → 下载解压

    Args:
        pdf_path: PDF 文件路径

    Returns:
        解析后的 Markdown 文件路径，失败返回空字符串
    """
    filename = os.path.basename(pdf_path)
    pdf_name = os.path.splitext(filename)[0]

    print(f"\n[步骤 1] 调用 MinerU API 解析：{filename}")

    # 检查 Token
    if not MINERU_TOKEN:
        print("  [错误] 未配置 MINERU_TOKEN，请在 .env 文件中设置")
        return ""

    # 步骤 1：获取上传链接
    print("  获取上传链接...")
    result = get_upload_urls(filename)
    if not result:
        return ""

    batch_id, file_url = result

    # 步骤 2：上传文件
    print("  上传文件...")
    if not upload_file(pdf_path, file_url):
        return ""

    # 步骤 3：轮询结果
    print("  等待解析完成...")
    zip_url = poll_result(batch_id)
    if not zip_url:
        return ""

    # 步骤 4：下载并解压
    # 解压到 data/processed/{pdf_name}/ 目录
    output_dir = os.path.join(PROCESSED_DIR, pdf_name)
    os.makedirs(output_dir, exist_ok=True)

    if not download_and_extract(zip_url, output_dir, pdf_name):
        return ""

    # 返回生成的 Markdown 文件路径
    md_path = os.path.join(output_dir, f"{pdf_name}.md")
    if os.path.exists(md_path):
        print(f"  [成功] 解析完成：{md_path}")
        return md_path
    else:
        print(f"  [错误] 未找到生成的 Markdown 文件")
        return ""


def run_vectorize(md_path: str) -> int:
    """
    对 Markdown 文件进行向量化存储

    Args:
        md_path: Markdown 文件路径

    Returns:
        存储的 chunk 数量，失败返回 0
    """
    filename = os.path.basename(md_path)
    print(f"\n[步骤 2] 向量化存储：{filename}")

    try:
        # 加载并切分文档
        print("  加载并切分文档...")
        chunks = load_and_split(md_path)
        print(f"  切分为 {len(chunks)} 个 chunk")

        if not chunks:
            print("  [警告] 文档切分结果为空，跳过向量化")
            return 0

        # 向量化并存储
        print("  调用 Embedding API 向量化...")
        start_time = time.time()
        count = add_documents(chunks)
        elapsed = time.time() - start_time

        print(f"  [成功] 存储完成，共 {count} 个文档，耗时 {elapsed:.2f} 秒")
        return count

    except Exception as e:
        print(f"  [错误] 向量化存储失败：{type(e).__name__}: {e}")
        return 0


def import_single_file(pdf_path: str, force: bool = False) -> bool:
    """
    导入单个 PDF 文件

    完整流程：检查更新 → MinerU 解析 → 向量化存储 → 记录状态

    Args:
        pdf_path: PDF 文件的绝对路径
        force: 是否强制重新导入（忽略更新检查）

    Returns:
        是否导入成功
    """
    # 使用相对路径作为唯一标识
    relative_path = get_relative_path(pdf_path)

    # 检查文件是否已更新
    if not force and is_imported(relative_path):
        if is_file_updated(relative_path, pdf_path):
            print(f"\n[更新] 检测到文件已更新：{relative_path}")
        else:
            print(f"\n[跳过] {relative_path} 已导入过")
            return True

    print(f"\n{'=' * 60}")
    print(f"开始导入：{relative_path}")
    print('=' * 60)

    # 步骤 1：MinerU 解析
    md_path = run_mineru_parse(pdf_path)
    if not md_path:
        mark_imported(relative_path, chunks_count=0, status="failed", file_path=pdf_path)
        return False

    # 步骤 2：向量化存储
    chunks_count = run_vectorize(md_path)
    if chunks_count == 0:
        mark_imported(relative_path, chunks_count=0, status="failed", file_path=pdf_path)
        return False

    # 记录导入成功
    mark_imported(relative_path, chunks_count=chunks_count, status="success", file_path=pdf_path)
    print(f"\n[完成] {relative_path} 导入成功，共 {chunks_count} 个 chunk")
    return True


def show_status():
    """
    显示当前导入状态

    打印知识库的详细状态信息，包括：
    - 统计信息（总文件数、成功/失败数、chunk 总数）
    - 已导入文件列表（状态、chunk 数、导入时间）
    - 待导入文件（新增、更新、删除）
    """
    from app.rag.imported_files import get_imported_files, find_deleted_files, find_new_files, find_updated_files

    print("=" * 60)
    print("知识库导入状态")
    print("=" * 60)

    # 显示统计信息
    stats = get_import_stats()
    print(f"\n统计信息：")
    print(f"  已导入文件：{stats['total_files']} 个")
    print(f"  成功：{stats['success_files']} 个")
    print(f"  失败：{stats['failed_files']} 个")
    print(f"  总 chunk 数：{stats['total_chunks']} 个")

    # 显示已导入文件列表
    files = get_imported_files()
    if files:
        print(f"\n已导入文件列表：")
        for f in files:
            status_icon = "[OK]" if f["status"] == "success" else "[FAIL]"
            print(f"  {status_icon} {f['filename']}")
            print(f"    chunks: {f.get('chunks_count', 0)}, 状态: {f['status']}")
            print(f"    导入时间: {f.get('imported_at', 'N/A')}")
    else:
        print("\n暂无导入记录")

    # 扫描当前 PDF 文件，检测变化
    pdf_files = scan_pdf_files()
    deleted_files = find_deleted_files()
    new_files = find_new_files(pdf_files)
    updated_files = find_updated_files(pdf_files)

    # 显示待处理文件
    if deleted_files or new_files or updated_files:
        print(f"\n待处理文件：")
        if deleted_files:
            print(f"  [删除] {len(deleted_files)} 个文件需要清理：")
            for f in deleted_files:
                print(f"    - {f['filename']}")
        if new_files:
            print(f"  [新增] {len(new_files)} 个新文件待导入：")
            for f in new_files:
                print(f"    - {get_relative_path(f)}")
        if updated_files:
            print(f"  [更新] {len(updated_files)} 个文件需要重新导入：")
            for f in updated_files:
                print(f"    - {get_relative_path(f)}")
    else:
        print("\n所有文件状态正常，无需操作。")


def main():
    """
    主函数：递归扫描并导入所有未导入的 PDF 文件

    支持命令行参数：
        --force: 强制重新导入所有文件
        --reimport KEYWORD: 重新导入包含关键词的文件
        --status: 查看导入状态

    处理逻辑：
        1. 检测已删除的文件（PDF 不存在，但 JSON 有记录）→ 清理 MD 和向量数据
        2. 检测新增的文件（PDF 存在，但 JSON 没记录）→ 导入
        3. 检测更新的文件（JSON 有记录，但 PDF 时间更新）→ 重新导入
        4. 无变化的文件 → 跳过
    """
    parser = argparse.ArgumentParser(
        description="智科云联 - 知识库一键导入工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  # 正常导入（跳过已导入的文件，自动检测更新和删除）
  python app/scripts/import_knowledge.py

  # 强制重新导入所有文件
  python app/scripts/import_knowledge.py --force

  # 重新导入指定文件（支持模糊匹配）
  python app/scripts/import_knowledge.py --reimport "01-实验前准备"

  # 重新导入失败的文件
  python app/scripts/import_knowledge.py --reimport-failed

  # 查看导入状态
  python app/scripts/import_knowledge.py --status
        """
    )

    parser.add_argument("--force", action="store_true",
                        help="强制重新导入所有文件（忽略已导入记录）")
    parser.add_argument("--reimport", type=str, metavar="KEYWORD",
                        help="重新导入包含指定关键词的文件")
    parser.add_argument("--reimport-failed", action="store_true",
                        help="重新导入之前导入失败的文件")
    parser.add_argument("--status", action="store_true",
                        help="查看当前导入状态")

    args = parser.parse_args()

    print("=" * 60)
    print("智科云联 - 知识库一键导入工具")
    print("=" * 60)

    # 显示状态模式
    if args.status:
        show_status()
        return

    # 显示当前统计信息
    stats = get_import_stats()
    print(f"\n当前知识库状态：")
    print(f"  已导入文件：{stats['total_files']} 个")
    print(f"  总 chunk 数：{stats['total_chunks']} 个")

    # 检查 MinerU Token
    if not MINERU_TOKEN:
        print("\n[错误] 未配置 MINERU_TOKEN，请在 .env 文件中设置")
        return

    # 强制重新导入模式
    if args.force:
        print(f"\n[模式] 强制重新导入所有文件")
        from app.rag.imported_files import clear_record
        from app.rag.vectorstore import clear_vectorstore

        # 清空导入记录
        clear_record()

        # 清空向量数据库，避免重复数据
        print("清空向量数据库...")
        clear_vectorstore()

    # 重新导入指定文件模式
    elif args.reimport:
        keyword = args.reimport
        print(f"\n[模式] 重新导入包含 '{keyword}' 的文件")
        from app.rag.imported_files import remove_records_by_keyword, find_imported_file

        # 查找匹配的文件
        matched = find_imported_file(keyword)
        if matched:
            print(f"找到 {len(matched)} 个匹配的已导入文件：")
            for f in matched:
                print(f"  - {f['filename']}")

            # 删除这些记录
            deleted = remove_records_by_keyword(keyword)
            print(f"已删除 {deleted} 条记录，将重新导入")
        else:
            print(f"未找到包含 '{keyword}' 的已导入文件")

    # 重新导入失败文件模式
    elif args.reimport_failed:
        print(f"\n[模式] 重新导入失败的文件")
        from app.rag.imported_files import load_record, save_record

        record = load_record()
        failed_files = [f for f in record["imported_files"] if f.get("status") == "failed"]

        if failed_files:
            print(f"找到 {len(failed_files)} 个失败的文件：")
            for f in failed_files:
                print(f"  - {f['filename']}")

            # 删除失败记录
            record["imported_files"] = [
                f for f in record["imported_files"]
                if f.get("status") != "failed"
            ]
            save_record(record)
            print(f"已删除失败记录，将重新导入")
        else:
            print("没有失败的文件需要重新导入")

    # 递归扫描 PDF 文件
    print(f"\n扫描目录：{RAW_DIR}（含所有子目录）")
    pdf_files = scan_pdf_files()

    if not pdf_files:
        print("\n未找到 PDF 文件，请将文件放入 data/raw/ 目录。")
        return

    # 显示所有 PDF 文件及其状态
    print(f"\n找到 {len(pdf_files)} 个 PDF 文件：")
    for pdf in pdf_files:
        relative_path = get_relative_path(pdf)
        if is_imported(relative_path):
            if is_file_updated(relative_path, pdf):
                status = "已更新"
            else:
                status = "已导入"
        else:
            status = "待导入"
        print(f"  - {relative_path} [{status}]")

    # ====== 检测已删除的文件 ======
    from app.rag.imported_files import find_deleted_files, delete_file_record
    deleted_files = find_deleted_files()

    if deleted_files:
        print(f"\n检测到 {len(deleted_files)} 个已删除的文件：")
        for f in deleted_files:
            print(f"  - {f['filename']}")
            delete_file_record(f['filename'])
            print(f"    [清理] 已删除 MD 文件和向量数据")

    # ====== 检测孤立的 MD 目录（processed 有 MD 但 JSON 无记录）======
    from app.rag.imported_files import find_orphan_md_dirs, cleanup_orphan_md_dirs
    orphan_dirs = find_orphan_md_dirs()

    if orphan_dirs:
        print(f"\n检测到 {len(orphan_dirs)} 个孤立的 MD 目录（无对应 PDF 记录）：")
        for d in orphan_dirs:
            print(f"  - {d}")
        cleaned = cleanup_orphan_md_dirs(orphan_dirs)
        print(f"  已清理 {cleaned} 个孤立目录")

    # ====== 检测新增和更新的文件 ======
    files_to_import = []
    for pdf in pdf_files:
        relative_path = get_relative_path(pdf)
        if not is_imported(relative_path):
            files_to_import.append(pdf)
        elif is_file_updated(relative_path, pdf):
            files_to_import.append(pdf)

    if not files_to_import:
        print("\n所有文件都已导入且未更新，无需操作。")
        return

    print(f"\n需要导入 {len(files_to_import)} 个文件（新文件或已更新文件）")

    # 逐个导入
    success_count = 0
    for pdf_path in files_to_import:
        if import_single_file(pdf_path, force=args.force):
            success_count += 1

    # 显示最终统计
    print("\n" + "=" * 60)
    print("导入完成！")
    print("=" * 60)

    stats = get_import_stats()
    print(f"\n最终统计：")
    print(f"  本次导入：{success_count}/{len(files_to_import)} 个文件")
    print(f"  知识库总计：{stats['total_files']} 个文件，{stats['total_chunks']} 个 chunk")
    print(f"\n下一步：运行 python web/app.py 启动问答系统")


if __name__ == "__main__":
    main()
