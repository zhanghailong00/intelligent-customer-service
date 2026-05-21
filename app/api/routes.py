"""
API 路由模块
定义 FastAPI 接口，处理 HTTP 请求
"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.llm.models import chat
from app.rag.retriever import retrieve

# 创建路由器
router = APIRouter()


# ==================== 请求/响应模型 ====================

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str      # 用户消息
    history: list = []  # 对话历史


class ChatResponse(BaseModel):
    """聊天响应模型"""
    reply: str        # LLM 回复
    sources: list = []  # 参考的文档来源


# ==================== API 接口 ====================

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    聊天接口

    流程：
    1. 根据用户问题检索相关文档
    2. 将文档作为上下文，调用 LLM 生成回答
    3. 返回回答和参考来源
    """
    # 1. 检索相关文档
    docs = retrieve(request.message)

    # 2. 构建 prompt（将检索到的文档作为上下文）
    context = "\n".join(docs) if docs else "未找到相关信息"
    messages = [
        {"role": "system", "content": f"你是一个智能客服助手。根据以下信息回答用户问题：\n{context}"},
        {"role": "user", "content": request.message}
    ]

    # 3. 调用 LLM 生成回答
    reply = chat(messages)

    # 4. 返回回答和参考来源
    return ChatResponse(reply=reply, sources=docs)
