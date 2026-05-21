# 面试亮点：LLM Fallback 兜底 机制

**日期**：2026-05-21
**项目**：智科云联 - 实训设备智能客服系统
**技术栈**：DeepSeek + 通义千问 + LangChain + ChromaDB

---

## 一、问题背景

在生产环境中，LLM 服务可能因为以下原因不可用：
- **服务过载**：高峰期 API 返回 503 错误
- **网络波动**：临时网络故障导致超时
- **服务维护**：模型升级或维护期间服务中断

**真实案例**：
```
DeepSeek API 返回 503 错误：
"Service is too busy. We advise users to temporarily switch to
alternative LLM API service providers."
```

如果单一依赖主模型，服务会完全不可用，影响用户体验。

---

## 二、解决方案：Fallback 兜底机制

### 架构设计

```
用户请求
    ↓
┌─────────────────────┐
│   主模型 (DeepSeek)  │
│   - 快速响应         │
│   - 成本较低         │
└──────────┬──────────┘
           │ 失败
           ↓
┌─────────────────────┐
│  备用模型 (通义千问)  │
│   - 自动接管         │
│   - 服务降级         │
└──────────┬──────────┘
           │ 成功
           ↓
      返回响应
```

### 核心代码

```python
def chat(messages: list, temperature: float = 0.7) -> str:
    """
    与 LLM 对话（支持 Fallback 机制）
    主模型调用失败时，自动切换到备用模型继续服务。
    """
    # 1. 尝试调用主模型
    try:
        primary_llm = get_llm(temperature, provider="primary")
        result = _call_llm(primary_llm, lc_messages)
        print(f"[LLM] 主模型 ({DEEPSEEK_MODEL}) 调用成功")
        return result
    except Exception as e:
        print(f"[LLM] 主模型失败: {type(e).__name__}: {e}")

        # 2. 如果未启用 Fallback，直接抛出
        if not LLM_FALLBACK_ENABLED:
            raise

        # 3. Fallback 到备用模型
        print(f"[LLM] 触发 Fallback，切换到备用模型...")
        try:
            fallback_llm = get_llm(temperature, provider="fallback")
            result = _call_llm(fallback_llm, lc_messages)
            print(f"[LLM] 备用模型调用成功")
            return result
        except Exception as fallback_error:
            print(f"[LLM] 备用模型也失败了")
            raise Exception(f"主模型和备用模型均调用失败")
```

---

## 三、技术亮点

### 1. 自动故障检测与切换
- **无需人工干预**：主模型异常时自动触发 Fallback
- **无缝切换**：用户无感知，服务不中断
- **实时日志**：记录切换过程，便于监控和排查

### 2. 配置化管理
```python
# config.py - 灵活配置
LLM_FALLBACK_ENABLED = True  # 是否启用 Fallback
LLM_PRIMARY_TIMEOUT = 30     # 主模型超时时间
LLM_FALLBACK_TIMEOUT = 60    # 备用模型超时时间
```

### 3. 状态追踪
```python
def chat_with_fallback_status(...) -> dict:
    """返回详细的调用状态"""
    return {
        "answer": result,
        "provider": "primary" or "fallback",  # 实际使用的模型
        "model": "deepseek-chat" or "qwen-plus",
        "fallback_triggered": True or False    # 是否触发了 Fallback
    }
```

### 4. 生产级考虑
- **超时控制**：防止长时间阻塞
- **错误分类**：区分可恢复和不可恢复错误
- **降级策略**：服务降级而非服务中断

---

## 四、面试话术

### 问题引入
> "在实际生产中，LLM 服务可能因为各种原因不可用。我在项目中设计了 Fallback 兜底机制，当主模型（DeepSeek）调用失败时，自动切换到备用模型（通义千问），确保服务可用性。"

### 技术细节
> "具体实现上，我用了 Try-Catch 捕获主模型异常，根据异常类型判断是否触发 Fallback。同时实现了配置化管理，可以通过配置开关控制是否启用 Fallback，以及设置超时时间。"

### 价值总结
> "这个方案实现了服务降级而非服务中断，是生产级 AI 应用必备的高可用方案。即使 DeepSeek 服务不可用，用户仍然可以获得回答，只是可能响应稍慢一些。"

---

## 五、扩展思考

### 1. 更复杂的 Fallback 策略
- **多级 Fallback**：主 → 备1 → 备2
- **负载均衡**：多个模型轮询
- **性能优先**：根据响应时间选择模型

### 2. 监控与告警
- **Fallback 触发率**：监控主模型健康状态
- **响应时间对比**：主备模型性能对比
- **成本分析**：不同模型的调用成本

### 3. 熔断机制
- **连续失败阈值**：连续 N 次失败后暂停主模型
- **自动恢复**：定期尝试恢复主模型调用

---

## 六、相关代码文件

| 文件 | 说明 |
|---|---|
| `app/config.py` | LLM 和 Fallback 配置 |
| `app/llm/models.py` | Fallback 机制实现 |
| `.env` | API Key 配置 |

---

## 七、面试加分点

1. **真实场景驱动**：从实际遇到的 503 错误出发，不是为了用而用
2. **生产级思维**：考虑了超时、降级、监控等生产环境需求
3. **代码质量**：清晰的日志、配置化、状态追踪
4. **扩展性**：为后续的多级 Fallback、熔断机制留好接口

---

*记录时间：2026-05-21*
*项目：智科云联 - 实训设备智能客服系统*
