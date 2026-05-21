"""调试 API 连接"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

print("=" * 50)
print("API 调试信息")
print("=" * 50)
print(f"API Key: {DEEPSEEK_API_KEY[:10]}..." if DEEPSEEK_API_KEY else "API Key: 未设置")
print(f"Base URL: {DEEPSEEK_BASE_URL}")
print(f"Model: {DEEPSEEK_MODEL}")
print("=" * 50)

if not DEEPSEEK_API_KEY:
    print("错误：DEEPSEEK_API_KEY 未设置，请检查 .env 文件")
else:
    print("尝试调用 API...")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=50
        )
        print("成功！响应:", response.choices[0].message.content)
    except Exception as e:
        print(f"错误: {type(e).__name__}: {e}")
