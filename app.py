"""
Hugging Face Spaces 入口文件

功能：
- 导入 web/app.py 中的 Gradio 界面
- 作为 Hugging Face Spaces 的启动入口

部署说明：
1. 在 Hugging Face 创建 Space，选择 Gradio SDK
2. 上传整个项目代码
3. 在 Space Settings → Repository secrets 中配置环境变量：
   - DEEPSEEK_API_KEY: DeepSeek API 密钥
   - QWEN_API_KEY: 通义千问 API 密钥
   - QWEN_LLM_API_KEY: 通义千问 LLM API 密钥
4. Space 会自动运行此文件，启动 Gradio 界面
"""
"""
Hugging Face Spaces 入口文件
"""

import os
import sys

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入 Gradio 界面
from web.app import demo

# 启动 Gradio 服务
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860
    )