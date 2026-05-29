"""
知识库管理后台

功能：
- 上传文档（PDF）
- 查看已导入文档列表
- 删除文档
- 重新导入文档

启动命令：python web/admin.py
"""
import os
import sys

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import gradio as gr
from app.rag.imported_files import get_imported_files, get_import_stats


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


# 创建 Gradio 界面
with gr.Blocks(title="知识库管理后台") as demo:
    gr.Markdown("# 知识库管理后台")
    gr.Markdown("管理实训设备智能客服的知识库文档")

    # 统计信息
    stats_text = gr.Markdown(value=get_stats_text())

    # 文档列表
    gr.Markdown("## 已导入文档")
    doc_list = gr.Dataframe(
        headers=["文件名", "状态", "chunk数", "导入时间"],
        value=get_doc_list(),
        interactive=False
    )

    # 刷新按钮
    refresh_btn = gr.Button("刷新列表")

    def refresh_list():
        """刷新文档列表"""
        return get_doc_list(), get_stats_text()

    refresh_btn.click(
        fn=refresh_list,
        outputs=[doc_list, stats_text]
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
