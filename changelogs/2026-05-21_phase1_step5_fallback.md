# 改动摘要：LLM Fallback 兜底机制

**日期**：2026-05-21
**操作人**：Claude
**任务**：实现主备 LLM 自动切换，提升服务可用性

---

## 改动文件列表

### 1. 修改文件

| 文件 | 说明 |
|---|---|
| `app/config.py` | 添加通义千问 LLM 配置和 Fallback 配置 |
| `app/llm/models.py` | 实现 Fallback 机制 |
| `web/app.py` | 修复 Gradio 界面兼容性 |

### 2. 新增文件

| 文件 | 说明 |
|---|---|
| `interview_highlights/01_llm_fallback_mechanism.md` | 面试亮点文档 |
| `test_api_debug.py` | API 调试脚本 |
| `changelogs/2026-05-21_phase1_step5_fallback.md` | 本改动摘要 |

---

## 每个文件的改动详情

### app/config.py（修改）

**新增配置项：**
```python
# 通义千问 LLM 配置（备用模型）
QWEN_LLM_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_LLM_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_LLM_MODEL = "qwen-plus"

# LLM Fallback 配置
LLM_PRIMARY_TIMEOUT = 30    # 主模型超时时间
LLM_FALLBACK_TIMEOUT = 60   # 备用模型超时时间
LLM_FALLBACK_ENABLED = True # 是否启用 Fallback
```

**为什么这样设计：**
- 配置化管理，便于调整
- 超时控制，防止长时间阻塞
- 开关控制，灵活启停

---

### app/llm/models.py（重写）

**核心功能：**
1. `get_llm(provider, timeout)`: 获取 LLM 实例，支持主备切换
2. `chat(messages, temperature)`: 对话接口，自动 Fallback
3. `chat_with_fallback_status(messages, temperature)`: 带状态追踪的对话接口

**Fallback 流程：**
```
1. 尝试调用主模型（DeepSeek）
2. 捕获异常（超时、503、网络错误等）
3. 如果启用 Fallback，切换到备用模型（通义千问）
4. 返回结果，记录使用的模型
```

**关键代码：**
```python
try:
    # 主模型调用
    result = _call_llm(primary_llm, lc_messages)
    return result
except Exception as e:
    print(f"[LLM] 主模型失败: {e}")
    if not LLM_FALLBACK_ENABLED:
        raise
    # Fallback 到备用模型
    fallback_llm = get_llm(temperature, provider="fallback")
    result = _call_llm(fallback_llm, lc_messages)
    return result
```

**为什么这样设计：**
- 自动故障检测，无需人工干预
- 无缝切换，用户无感知
- 状态追踪，便于监控和调试

---

### interview_highlights/01_llm_fallback_mechanism.md（新增）

**内容：**
- 问题背景（DeepSeek 503 错误）
- 解决方案（架构图、核心代码）
- 技术亮点（自动切换、配置化、状态追踪）
- 面试话术（问题引入、技术细节、价值总结）
- 扩展思考（多级 Fallback、监控告警、熔断机制）

**用途：**
- 面试时快速回顾技术亮点
- 为后续类似功能提供参考

---

## 测试结果

**测试场景：** DeepSeek 服务不可用（超时/503）

**测试输出：**
```
[LLM] 主模型 (deepseek-chat) 调用失败: APITimeoutError: Request timed out.
[LLM] 触发 Fallback，切换到备用模型 (qwen-plus)...
[LLM] 备用模型 (qwen-plus) 调用成功，耗时: 4.32s

实际使用的模型: qwen-plus
是否触发 Fallback: True
```

**验证点：**
- ✓ 主模型异常自动捕获
- ✓ 自动切换到备用模型
- ✓ 备用模型调用成功
- ✓ 服务降级而非中断

---

## 潜在风险

| 风险 | 说明 | 缓解措施 |
|---|---|---|
| 备用模型也失败 | 两个模型都不可用 | 返回明确错误信息 |
| 成本增加 | 备用模型调用产生额外费用 | 配置开关控制 |
| 响应时间变长 | Fallback 需要两次调用 | 设置合理超时时间 |

---

## 接口兼容性

| 接口 | 状态 | 说明 |
|---|---|---|
| `chat()` | 重写 | 新增 Fallback 逻辑，接口不变 |
| `chat_with_fallback_status()` | 新增 | 返回详细调用状态 |

---

## 回滚方案

如果出现问题，可以：
1. 设置 `LLM_FALLBACK_ENABLED = False` 禁用 Fallback
2. 恢复 `app/llm/models.py` 到之前版本

---

## 面试亮点

这个功能是**生产级 AI 应用的必备高可用方案**，面试时可以重点介绍：

1. **真实场景驱动**：从实际遇到的 503 错误出发
2. **自动故障转移**：无需人工干预，服务不中断
3. **生产级设计**：超时控制、配置化、状态追踪
4. **可扩展性**：为多级 Fallback、熔断机制留好接口

详见 `interview_highlights/01_llm_fallback_mechanism.md`
