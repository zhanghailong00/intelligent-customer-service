"""
文档加载模块
负责加载 Markdown 文档，按标题层级切分，提取元数据

source 格式说明：
使用相对于 data/processed/ 的完整路径（含子目录），
例如 "实验箱前期准备工作\\01-实验前准备\\01-实验前准备.md"
确保不同子目录下同名文件的 source 全局唯一。
"""
import os
import re
from typing import List, Dict


def load_markdown(file_path: str) -> str:
    """
    读取 Markdown 文件内容

    Args:
        file_path: Markdown 文件路径

    Returns:
        文件内容
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def split_by_headers(content: str, source_file: str) -> List[Dict]:
    """
    按标题层级切分 Markdown 文档

    切分规则：
    - 遇到 # ## ### 等标题时，创建新的 chunk
    - 每个标题下的内容（直到下一个标题）是一个 chunk

    Args:
        content: Markdown 内容
        source_file: 源文件名

    Returns:
        切分后的 chunk 列表
    """
    chunks = []
    lines = content.split("\n")

    current_chunk = None

    for line in lines:
        # 检测标题行（# ## ### 等）
        header_match = re.match(r'^(#{1,3})\s+(.+)', line)

        if header_match:
            # 保存上一个 chunk
            if current_chunk and current_chunk["content"].strip():
                chunks.append(current_chunk)

            # 创建新 chunk
            level = len(header_match.group(1))  # 标题级别（1-3）
            title = header_match.group(2).strip()

            current_chunk = {
                "content": f"{'#' * level} {title}\n",
                "metadata": {
                    "source": source_file,
                    "chapter": title,
                    "parent_chapter": "",
                    "level": level
                }
            }
        elif current_chunk:
            # 追加内容到当前 chunk
            current_chunk["content"] += line + "\n"

    # 保存最后一个 chunk
    if current_chunk and current_chunk["content"].strip():
        chunks.append(current_chunk)

    # 设置上级标题
    _set_parent_chapters(chunks)

    # 清理 chunk 内容
    _clean_chunks(chunks)

    return chunks


def _set_parent_chapters(chunks: List[Dict]):
    """
    根据标题层级设置上级标题

    例如：
    - # 实验环境的搭建 → parent_chapter = ""
    - ## 配置和启动实验平台虚拟环境 → parent_chapter = "实验环境的搭建"
    - ### 子标题 → parent_chapter = "配置和启动实验平台虚拟环境"
    """
    chapter_stack = []  # 维护标题栈

    for chunk in chunks:
        level = chunk["metadata"]["level"]

        # 弹出同级或更低级别的标题
        while chapter_stack and chapter_stack[-1]["level"] >= level:
            chapter_stack.pop()

        # 设置上级标题
        if chapter_stack:
            chunk["metadata"]["parent_chapter"] = chapter_stack[-1]["title"]
        else:
            chunk["metadata"]["parent_chapter"] = ""

        # 将当前标题入栈
        chapter_stack.append({
            "title": chunk["metadata"]["chapter"],
            "level": level
        })


def _clean_chunks(chunks: List[Dict]):
    """
    清理 chunk 内容

    - 移除多余的空行
    - 移除 <details> 标签内容（MinerU 自动生成的图片描述）
    """
    for chunk in chunks:
        content = chunk["content"]

        # 移除 <details> 标签及内容
        content = re.sub(r'<details>.*?</details>', '', content, flags=re.DOTALL)

        # 移除多余空行（保留最多 2 个连续空行）
        content = re.sub(r'\n{3,}', '\n\n', content)

        # 清理首尾空白
        content = content.strip()

        chunk["content"] = content


def load_and_split(file_path: str) -> List[Dict]:
    """
    加载并切分 Markdown 文件

    Args:
        file_path: Markdown 文件路径

    Returns:
        切分后的 chunk 列表

    注意：source 使用相对于 data/processed/ 的完整路径（含子目录），
    例如 "实验箱前期准备工作\\01-实验前准备.md"，确保全局唯一，
    避免不同子目录下同名文件的向量数据互相覆盖。
    """
    # 使用相对于 processed 目录的路径作为 source，确保全局唯一
    # 例如："实验箱前期准备工作\\01-实验前准备.md"
    processed_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "processed")
    source_file = os.path.relpath(file_path, processed_dir).replace("/", "\\")
    content = load_markdown(file_path)
    chunks = split_by_headers(content, source_file)
    return chunks
