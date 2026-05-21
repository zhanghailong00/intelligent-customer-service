"""
配置管理模块
加载环境变量，统一管理项目配置
"""
import os
from dotenv import load_dotenv

# 项目根目录（config.py 的上两级目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 加载 .env 文件中的环境变量
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# ==================== DeepSeek LLM 配置 ====================
# DeepSeek API 密钥，用于调用大语言模型
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
# DeepSeek API 基础地址
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
# 使用的模型名称
DEEPSEEK_MODEL = "deepseek-chat"

# ==================== 通义千问 Embedding 配置 ====================
# 通义千问 API 密钥，用于文本向量化
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
# 向量化模型名称
QWEN_EMBEDDING_MODEL = "tongyi-embedding-vision-flash-2026-03-06"

# ==================== ChromaDB 向量数据库配置 ====================
# 向量数据库持久化存储目录（使用绝对路径，确保在任何目录运行都能找到）
CHROMA_PERSIST_DIR = os.path.join(PROJECT_ROOT, "chroma_db")
# 向量数据库集合名称
CHROMA_COLLECTION_NAME = "knowledge_base"

# ==================== RAG 检索配置 ====================
# 检索返回的最相关文档数量
RETRIEVAL_TOP_K = 3
# 文档切分的块大小（字符数）
CHUNK_SIZE = 500
# 文档切分时的重叠字符数
CHUNK_OVERLAP = 50

# ==================== Gradio 界面配置 ====================
# Gradio 服务监听地址
GRADIO_HOST = "0.0.0.0"
# Gradio 服务端口
GRADIO_PORT = 7860
