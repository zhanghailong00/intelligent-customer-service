---
title: 实训设备智能客服
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 5.0.0
app_file: app.py
pinned: false
license: mit
---

# 智科云联 - 实训设备智能客服

基于多 Agent + RAG + HITL 架构的实训设备智能客服系统。

## 功能特性

- **多 Agent 路由**：自动识别问题类型，分发给专业 Agent
- **RAG 检索**：基于知识库的智能问答
- **HITL 人工介入**：AI 无法处理时自动转人工
- **会话快照**：转人工时自动生成核心诉求和建议方案
- **查询改写**：基于历史对话改写用户问题，提升检索质量

## 技术栈

- Python / LangChain / LangGraph
- ChromaDB 向量数据库
- DeepSeek API + 通义千问
- Gradio 界面

## 环境变量配置

在 Space Settings → Repository secrets 中配置：

| 变量名 | 说明 |
|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `QWEN_API_KEY` | 通义千问 API 密钥 |
| `QWEN_LLM_API_KEY` | 通义千问 LLM API 密钥 |

## 使用方法

直接在聊天框输入问题即可：

- "如何搭建实验环境？"
- "传感器不亮了怎么办？"
- "输入输出设备怎么选择？"
