"""
测试 MinerU 精准解析 API
将 PDF 转换为 Markdown 格式（支持图片提取）

使用说明：不要开启 VPN，直接运行即可
"""
import requests
import time
import os
import zipfile
import io
from dotenv import load_dotenv

# 加载环境变量（从项目根目录的 .env 文件）
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"))

# MinerU API 配置
BASE_URL = "https://mineru.net/api/v4"
TOKEN = os.getenv("MINERU_TOKEN")

# 请求头
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}


def get_upload_urls(file_name):
    """
    获取文件上传签名 URL

    Args:
        file_name: 文件名

    Returns:
        (batch_id, file_url) 或 None
    """
    url = f"{BASE_URL}/file-urls/batch"
    data = {
        "files": [{"name": file_name}],
        "model_version": "vlm"  # 使用 vlm 模型，精度更高
    }

    resp = requests.post(url, headers=HEADERS, json=data)
    result = resp.json()

    if result["code"] != 0:
        print(f"获取上传链接失败: {result['msg']}")
        return None

    batch_id = result["data"]["batch_id"]
    file_url = result["data"]["file_urls"][0]
    print(f"batch_id: {batch_id}")
    return batch_id, file_url


def upload_file(file_path, file_url):
    """
    上传文件到 OSS

    Args:
        file_path: 本地文件路径
        file_url: 上传 URL

    Returns:
        是否成功
    """
    with open(file_path, "rb") as f:
        resp = requests.put(file_url, data=f)

    if resp.status_code in (200, 201):
        print("文件上传成功")
        return True
    else:
        print(f"文件上传失败, HTTP {resp.status_code}")
        return False


def poll_result(batch_id, timeout=300, interval=3):
    """
    轮询查询解析结果

    Args:
        batch_id: 批量任务 ID
        timeout: 超时时间（秒）
        interval: 轮询间隔（秒）

    Returns:
        ZIP 下载链接，失败返回 None
    """
    url = f"{BASE_URL}/extract-results/batch/{batch_id}"
    start = time.time()

    while time.time() - start < timeout:
        resp = requests.get(url, headers=HEADERS)
        result = resp.json()

        if result["code"] != 0:
            print(f"查询失败: {result['msg']}")
            return None

        extract_result = result["data"]["extract_result"][0]
        state = extract_result["state"]
        elapsed = int(time.time() - start)

        if state == "done":
            zip_url = extract_result["full_zip_url"]
            print(f"[{elapsed}s] 解析完成")
            print(f"ZIP 下载链接: {zip_url}")
            return zip_url

        if state == "failed":
            err_msg = extract_result.get("err_msg", "未知错误")
            print(f"[{elapsed}s] 解析失败: {err_msg}")
            return None

        # 显示进度
        progress = extract_result.get("extract_progress", {})
        if progress:
            extracted = progress.get("extracted_pages", 0)
            total = progress.get("total_pages", 0)
            print(f"[{elapsed}s] {state} ({extracted}/{total} 页)...")
        else:
            print(f"[{elapsed}s] {state}...")

        time.sleep(interval)

    print(f"轮询超时 ({timeout}s)")
    return None


def download_and_extract(zip_url, output_dir, pdf_name):
    """
    下载并解压 ZIP 文件，只保留需要的文件

    Args:
        zip_url: ZIP 下载链接
        output_dir: 输出目录
        pdf_name: 原始 PDF 文件名（不含扩展名）

    Returns:
        解压后的文件列表
    """
    print("下载 ZIP 文件...")
    resp = requests.get(zip_url)

    if resp.status_code != 200:
        print(f"下载失败, HTTP {resp.status_code}")
        return None

    # 解压 ZIP
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(output_dir)
        file_list = zf.namelist()
        print(f"解压完成，共 {len(file_list)} 个文件")

        # 清理不需要的文件，只保留 full.md 和 images/
        cleanup_unnecessary_files(output_dir, file_list)

        # 重命名 full.md 为与 PDF 文件名相同
        rename_markdown(output_dir, pdf_name)

        return file_list


def cleanup_unnecessary_files(output_dir, file_list):
    """
    清理解析结果中的冗余文件

    只保留：
    - full.md（Markdown 主文件）
    - images/ 目录（图片文件）

    删除：
    - *.json（布局信息、内容列表）
    - *_origin.pdf（原始 PDF 副本）
    """
    print("\n清冗余文件...")

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

        # 删除 layout.json
        if file_name == "layout.json":
            should_delete = True

        if should_delete and os.path.exists(file_path):
            os.remove(file_path)
            deleted_count += 1
            print(f"  删除: {file_name}")

    print(f"清理完成，删除了 {deleted_count} 个冗余文件")


def rename_markdown(output_dir, pdf_name):
    """
    重命名 full.md 为与 PDF 文件名相同

    Args:
        output_dir: 输出目录
        pdf_name: PDF 文件名（不含扩展名）
    """
    old_path = os.path.join(output_dir, "full.md")
    new_path = os.path.join(output_dir, f"{pdf_name}.md")

    if os.path.exists(old_path):
        os.rename(old_path, new_path)
        print(f"重命名: full.md -> {pdf_name}.md")


if __name__ == "__main__":
    # 配置
    pdf_path = "data/raw/02-实验环境的搭建.pdf"
    output_dir = "data/processed"

    print("=" * 50)
    print("MinerU 精准解析 API 测试")
    print("=" * 50)
    print(f"文件: {pdf_path}")
    print("=" * 50)

    # 1. 获取上传链接
    file_name = os.path.basename(pdf_path)
    result = get_upload_urls(file_name)
    if not result:
        exit(1)

    batch_id, file_url = result

    # 2. 上传文件
    if not upload_file(pdf_path, file_url):
        exit(1)

    # 3. 轮询结果
    zip_url = poll_result(batch_id)
    if not zip_url:
        exit(1)

    # 4. 下载并解压
    pdf_name = os.path.splitext(file_name)[0]
    file_list = download_and_extract(zip_url, output_dir, pdf_name)
    if file_list:
        print("\n" + "=" * 50)
        print("解析完成！文件列表：")
        print("=" * 50)
        for f in file_list:
            print(f"  - {f}")
