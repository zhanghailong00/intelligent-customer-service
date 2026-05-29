"""
知识库管理后台

功能：
- 上传文档（PDF）
- 查看已导入文档列表
- 删除文档

启动命令：python web/admin.py
"""
import os
import sys
import shutil

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import gradio as gr
from app.rag.imported_files import get_imported_files, get_import_stats, delete_file_record

# 数据目录
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")


def get_doc_list():
    """
    获取文档列表，格式化为 Gradio Dataframe 数据

    Returns:
        文档列表数据，格式：[[文件名, 状态, chunk数, 导入时间], ...]
    """
    files = get_imported_files()
    if not files:
        return []

    data = []
    for f in files:
        data.append([
            f.get("filename", ""),
            f.get("status", ""),
            f.get("chunks_count", 0),
            f.get("imported_at", "")[:19] if f.get("imported_at") else ""
        ])
    return data


def get_stats_text():
    """
    获取统计信息文本

    Returns:
        统计信息字符串
    """
    stats = get_import_stats()
    return f"已导入 {stats['total_files']} 个文档，共 {stats['total_chunks']} 个 chunk"


def upload_and_process(file):
    """
    上传并处理文档

    流程：
    1. 保存文件到 data/raw/
    2. 调用 import_single_file 处理
    3. 更新列表和下拉框

    Args:
        file: Gradio 上传的文件对象

    Returns:
        (文档列表, 统计信息, 状态消息, 下拉框选项)
    """
    if file is None:
        return get_doc_list(), get_stats_text(), "请选择文件", gr.update(choices=get_filename_choices())

    try:
        # 获取文件名
        filename = os.path.basename(file.name)

        # 确保 data/raw/ 目录存在
        os.makedirs(RAW_DIR, exist_ok=True)

        # 保存文件到 data/raw/
        dest_path = os.path.join(RAW_DIR, filename)
        shutil.copy(file.name, dest_path)
        print(f"[Admin] 文件已保存：{dest_path}")

        # 调用现有的导入逻辑
        from app.scripts.import_knowledge import import_single_file
        success = import_single_file(dest_path)

        # 刷新下拉框选项
        choices = get_filename_choices()
        doc_data = get_doc_list()
        stats = get_stats_text()

        if success:
            return doc_data, stats, f"上传成功：{filename}", gr.update(choices=choices)
        else:
            return doc_data, stats, f"上传成功但处理失败：{filename}", gr.update(choices=choices)

    except Exception as e:
        print(f"[Admin] 上传处理失败：{type(e).__name__}: {e}")
        return get_doc_list(), get_stats_text(), f"上传失败：{str(e)}", gr.update(choices=get_filename_choices())


def delete_document(filename):
    """
    删除文档

    流程：
    1. 删除 data/raw/ 中的 PDF 文件
    2. 删除 data/processed/ 中的 MD 目录
    3. 删除导入记录和向量数据（调用 delete_file_record）
    4. 更新列表

    Args:
        filename: 文件名（从下拉框选择）

    Returns:
        (文档列表, 统计信息, 状态消息, 下拉框选项)
    """
    if not filename:
        choices = get_filename_choices()
        return gr.update(value=get_doc_list()), get_stats_text(), "请选择要删除的文档", gr.update(choices=choices)

    try:
        # 1. 删除 data/raw/ 中的 PDF 文件
        pdf_path = os.path.join(RAW_DIR, filename)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            print(f"[Admin] 已删除 PDF 文件：{pdf_path}")

        # 2. 删除 data/processed/ 中的 MD 目录
        processed_dir = os.path.join(PROJECT_ROOT, "data", "processed")
        pdf_name = os.path.splitext(os.path.basename(filename))[0]
        md_dir = os.path.join(processed_dir, pdf_name)
        if os.path.exists(md_dir):
            shutil.rmtree(md_dir)
            print(f"[Admin] 已删除 MD 目录：{md_dir}")

        # 3. 删除导入记录和向量数据
        delete_file_record(filename)
        print(f"[Admin] 已删除导入记录：{filename}")

        # 4. 刷新下拉框选项
        choices = get_filename_choices()
        return gr.update(value=get_doc_list()), get_stats_text(), f"删除成功：{filename}", gr.update(choices=choices)

    except Exception as e:
        print(f"[Admin] 删除失败：{type(e).__name__}: {e}")
        return gr.update(value=get_doc_list()), get_stats_text(), f"删除失败：{str(e)}", gr.update(choices=get_filename_choices())


def get_filename_choices():
    """获取文件名列表（用于下拉框）"""
    files = get_imported_files()
    return [f.get("filename", "") for f in files]


def refresh_all():
    """刷新所有组件"""
    doc_data = get_doc_list()
    stats = get_stats_text()
    choices = get_filename_choices()
    return gr.update(value=doc_data), stats, "", gr.update(choices=choices)


# 创建 Gradio 界面
with gr.Blocks(title="知识库管理后台") as demo:
    gr.Markdown("# 知识库管理后台")
    gr.Markdown("管理实训设备智能客服的知识库文档")

    # 统计信息
    stats_text = gr.Markdown(value=get_stats_text())

    # 上传区域
    gr.Markdown("## 上传文档")
    with gr.Row():
        file_upload = gr.File(label="选择 PDF 文件", file_types=[".pdf"])
        upload_btn = gr.Button("上传并处理", variant="primary")

    # 上传状态
    upload_status = gr.Markdown(value="")

    # 删除区域
    gr.Markdown("## 删除文档")
    gr.Markdown("从下拉框中选择要删除的文档，然后点击删除按钮。")
    with gr.Row():
        delete_dropdown = gr.Dropdown(
            label="选择要删除的文档",
            choices=get_filename_choices(),
            interactive=True
        )
        delete_btn = gr.Button("删除", variant="stop")

    # 删除状态
    delete_status = gr.Markdown(value="")

    # 文档列表
    gr.Markdown("## 已导入文档")
    doc_list = gr.Dataframe(
        headers=["文件名", "状态", "chunk数", "导入时间"],
        value=get_doc_list(),
        interactive=False
    )

    # 刷新按钮
    refresh_btn = gr.Button("刷新列表")

    # 绑定事件
    upload_btn.click(
        fn=upload_and_process,
        inputs=[file_upload],
        outputs=[doc_list, stats_text, upload_status, delete_dropdown]
    )

    delete_btn.click(
        fn=delete_document,
        inputs=[delete_dropdown],
        outputs=[doc_list, stats_text, delete_status, delete_dropdown]
    )

    refresh_btn.click(
        fn=refresh_all,
        outputs=[doc_list, stats_text, upload_status, delete_dropdown]
    )


if __name__ == "__main__":
    print("=" * 60)
    print("知识库管理后台")
    print("=" * 60)
    print(f"项目根目录：{PROJECT_ROOT}")
    print("启动 Gradio 界面...")
    print("访问地址：http://localhost:7861")
    print("=" * 60)

    demo.launch(
        server_name="127.0.0.1",
        server_port=7861,
        share=False
    )
