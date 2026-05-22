"""
意图分类模块

功能：
- 使用 LLM 对用户问题进行意图分类
- 支持三种意图：产品咨询、故障排查、培训指导
- 输出结构化 JSON：意图类型 + 置信度

设计思路：
- 使用通用 Prompt，不要硬编码关键词
- LLM 自己判断意图，比规则更灵活
- 置信度低于阈值时，降级为兜底意图
"""
import json
import re
from typing import Dict, Optional
from app.llm.models import chat

# 意图类型常量
INTENT_PRODUCT = "product"      # 产品咨询
INTENT_FAULT = "fault"          # 故障排查
INTENT_TRAINING = "training"    # 培训指导
INTENT_GREETING = "greeting"    # 打招呼/闲聊
INTENT_UNKNOWN = "unknown"      # 无法识别

# 置信度阈值，低于此值视为无法识别
CONFIDENCE_THRESHOLD = 0.6

# 意图分类 Prompt（少样本提示）
INTENT_CLASSIFY_PROMPT = """你是一个智能客服系统的意图分类器。根据用户的问题，判断其意图属于以下哪一类：

1. **product**（产品咨询）：产品功能、参数、使用方法、规格说明
2. **fault**（故障排查）：设备故障、报错、异常、无法正常使用
3. **training**（培训指导）：教学资料、实验指导、课件、实验相关
4. **greeting**（打招呼）：问候、打招呼、自我介绍等非问题类输入

分类示例：
- "这个箱子有什么功能？" → {"intent": "product", "confidence": 0.95}
- "支持哪些传感器？" → {"intent": "product", "confidence": 0.9}
- "怎么连接WiFi？" → {"intent": "product", "confidence": 0.85}
- "传感器不亮了" → {"intent": "fault", "confidence": 0.9}
- "连不上网怎么办" → {"intent": "fault", "confidence": 0.85}
- "屏幕报错了" → {"intent": "fault", "confidence": 0.9}
- "有课件吗？" → {"intent": "training", "confidence": 0.9}
- "怎么做实验？" → {"intent": "training", "confidence": 0.85}
- "有教学视频吗？" → {"intent": "training", "confidence": 0.9}
- "你好" → {"intent": "greeting", "confidence": 0.95}
- "你是谁" → {"intent": "greeting", "confidence": 0.9}
- "早上好" → {"intent": "greeting", "confidence": 0.95}

边界判断规则：
- 涉及"实验/课件/教学/培训" → training
- 涉及"故障/报错/不亮/坏了/连不上" → fault
- 涉及"功能/参数/怎么用/规格/支持" → product
- 与实训设备完全无关的问题 → confidence < 0.5

输出格式（只输出 JSON，不要输出其他内容）：
{"intent": "product/fault/training/greeting", "confidence": 0.0-1.0}
"""


def classify_intent(user_query: str) -> Dict[str, any]:
    """
    对用户问题进行意图分类

    Args:
        user_query: 用户的问题文本

    Returns:
        分类结果字典：
        - intent: 意图类型（product/fault/training/unknown）
        - confidence: 置信度（0-1）
        - raw_response: LLM 原始响应（调试用）
    """
    # 构建消息
    messages = [
        {"role": "system", "content": INTENT_CLASSIFY_PROMPT},
        {"role": "user", "content": user_query}
    ]

    try:
        # 调用 LLM 进行分类
        raw_response = chat(messages, temperature=0.1)  # 低温度，结果更确定

        # 解析 JSON 响应
        result = _parse_intent_response(raw_response)

        # 检查置信度
        if result["confidence"] < CONFIDENCE_THRESHOLD:
            result["intent"] = INTENT_UNKNOWN

        result["raw_response"] = raw_response
        return result

    except Exception as e:
        print(f"[意图分类] 分类失败: {type(e).__name__}: {e}")
        return {
            "intent": INTENT_UNKNOWN,
            "confidence": 0.0,
            "raw_response": str(e)
        }


def _parse_intent_response(response: str) -> Dict[str, any]:
    """
    解析 LLM 的意图分类响应

    Args:
        response: LLM 的原始响应文本

    Returns:
        解析后的字典，包含 intent 和 confidence
    """
    # 尝试提取 JSON
    # 匹配 {...} 格式的 JSON
    json_match = re.search(r'\{[^}]+\}', response)

    if json_match:
        try:
            data = json.loads(json_match.group())
            intent = data.get("intent", INTENT_UNKNOWN)
            confidence = float(data.get("confidence", 0.0))

            # 验证 intent 值
            valid_intents = [INTENT_PRODUCT, INTENT_FAULT, INTENT_TRAINING, INTENT_GREETING]
            if intent not in valid_intents:
                intent = INTENT_UNKNOWN
                confidence = 0.0

            return {
                "intent": intent,
                "confidence": confidence
            }
        except (json.JSONDecodeError, ValueError):
            pass

    # 解析失败，返回未知
    return {
        "intent": INTENT_UNKNOWN,
        "confidence": 0.0
    }


def get_intent_label(intent: str) -> str:
    """
    获取意图的中文标签

    Args:
        intent: 意图类型代码

    Returns:
        中文标签
    """
    labels = {
        INTENT_PRODUCT: "产品咨询",
        INTENT_FAULT: "故障排查",
        INTENT_TRAINING: "培训指导",
        INTENT_GREETING: "打招呼",
        INTENT_UNKNOWN: "其他问题"
    }
    return labels.get(intent, "未知")


# 测试函数
if __name__ == "__main__":
    test_queries = [
        "这个箱子有什么功能？",
        "传感器不亮了",
        "有课件吗？",
        "你好",
        "你是谁",
        "今天天气怎么样？",
        "怎么连接WiFi？",
        "报错了怎么办？",
        "怎么做实验？",
    ]

    print("=" * 60)
    print("意图分类测试")
    print("=" * 60)

    for query in test_queries:
        result = classify_intent(query)
        label = get_intent_label(result["intent"])
        print(f"\n问题：{query}")
        print(f"意图：{label} ({result['intent']})")
        print(f"置信度：{result['confidence']:.2f}")
