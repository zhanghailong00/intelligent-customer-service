"""
智能客服系统 - FastAPI 主入口
启动命令：uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from app.api.routes import router

# 创建 FastAPI 应用实例
app = FastAPI(title="智能客服系统")

# 注册 API 路由，所有接口以 /api 开头
app.include_router(router, prefix="/api")


@app.get("/")
def root():
    """根路径，返回系统信息"""
    return {"message": "智能客服系统 API"}
