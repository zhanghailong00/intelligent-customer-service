"""
生成系统架构图
运行命令：python docs/generate_architecture.py
输出文件：docs/architecture.png
"""
from PIL import Image, ImageDraw, ImageFont
import os

# 画布尺寸
WIDTH = 1200
HEIGHT = 900
BG_COLOR = "#FFFFFF"

# 颜色方案
COLOR_TITLE = "#1a1a2e"
COLOR_BOX_NORMAL = "#4361ee"      # 蓝色：正常流程
COLOR_BOX_NORMAL_TEXT = "#FFFFFF"
COLOR_BOX_HITL = "#f72585"        # 粉色：HITL 相关
COLOR_BOX_HITL_TEXT = "#FFFFFF"
COLOR_BOX_AGENT = "#7209b7"       # 紫色：Agent
COLOR_BOX_AGENT_TEXT = "#FFFFFF"
COLOR_BOX_END = "#06d6a0"         # 绿色：终端节点
COLOR_BOX_END_TEXT = "#FFFFFF"
COLOR_BOX_DETECT = "#ff6b35"      # 橙色：前置检测
COLOR_BOX_DETECT_TEXT = "#FFFFFF"
COLOR_ARROW = "#555555"
COLOR_LABEL = "#333333"
COLOR_SUBTITLE = "#666666"


def draw_rounded_rect(draw, xy, radius, fill, outline=None):
    """绘制圆角矩形"""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def draw_arrow(draw, start, end, color=COLOR_ARROW, width=2):
    """绘制箭头"""
    draw.line([start, end], fill=color, width=width)
    # 箭头头部
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = (dx**2 + dy**2) ** 0.5
    if length == 0:
        return
    dx, dy = dx / length, dy / length
    arrow_size = 8
    # 箭头两侧点
    x, y = end
    left = (x - arrow_size * dx + arrow_size * 0.5 * dy,
            y - arrow_size * dy - arrow_size * 0.5 * dx)
    right = (x - arrow_size * dx - arrow_size * 0.5 * dy,
             y - arrow_size * dy + arrow_size * 0.5 * dx)
    draw.polygon([end, left, right], fill=color)


def draw_text_center(draw, pos, text, font, fill="#333333"):
    """居中绘制文本"""
    x, y = pos
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((x - tw // 2, y - th // 2), text, font=font, fill=fill)


def main():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 加载字体（使用系统默认字体）
    try:
        font_title = ImageFont.truetype("msyh.ttc", 28)
        font_box = ImageFont.truetype("msyh.ttc", 16)
        font_label = ImageFont.truetype("msyh.ttc", 13)
        font_small = ImageFont.truetype("msyh.ttc", 12)
    except OSError:
        try:
            font_title = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 28)
            font_box = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
            font_label = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 13)
            font_small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 12)
        except OSError:
            font_title = ImageFont.load_default()
            font_box = ImageFont.load_default()
            font_label = ImageFont.load_default()
            font_small = ImageFont.load_default()

    # ==================== 标题 ====================
    draw_text_center(draw, (WIDTH // 2, 35), "智科云联 - 实训设备智能客服系统架构", font_title, COLOR_TITLE)
    draw_text_center(draw, (WIDTH // 2, 65), "LangGraph 多智能体 + 双层 HITL 架构", font_subtitle if 'font_subtitle' in dir() else font_label, COLOR_SUBTITLE)

    # ==================== 定义节点位置 ====================
    # 格式: (center_x, center_y, width, height, text, color, text_color)

    # 用户输入
    user = (600, 110, 160, 40, "用户消息", COLOR_BOX_NORMAL, COLOR_BOX_NORMAL_TEXT)

    # classifier_node
    classifier = (600, 185, 200, 45, "classifier_node", COLOR_BOX_NORMAL, COLOR_BOX_NORMAL_TEXT)

    # 前置检测
    pre_detect = (350, 270, 180, 40, "前置检测（规则匹配）", COLOR_BOX_DETECT, COLOR_BOX_DETECT_TEXT)

    # LLM 分类
    llm_classify = (750, 270, 160, 40, "LLM 意图分类", COLOR_BOX_NORMAL, COLOR_BOX_NORMAL_TEXT)

    # 前置检测结果
    pre_result = (350, 345, 180, 35, "转人工/投诉/售后提示", COLOR_BOX_HITL, COLOR_BOX_HITL_TEXT)

    # 意图路由
    intent_route = (750, 355, 140, 35, "意图路由", COLOR_BOX_NORMAL, COLOR_BOX_NORMAL_TEXT)

    # greeting / unknown
    greeting = (500, 435, 120, 35, "greeting", COLOR_BOX_END, COLOR_BOX_END_TEXT)
    unknown = (700, 435, 120, 35, "unknown", COLOR_BOX_END, COLOR_BOX_END_TEXT)

    # Agent 节点
    agent_product = (900, 435, 140, 35, "product_agent", COLOR_BOX_AGENT, COLOR_BOX_AGENT_TEXT)
    agent_fault = (1050, 435, 140, 35, "fault_agent", COLOR_BOX_AGENT, COLOR_BOX_AGENT_TEXT)
    agent_training = (1050, 490, 140, 35, "training_agent", COLOR_BOX_AGENT, COLOR_BOX_AGENT_TEXT)

    # hitl_checker
    hitl_checker = (975, 570, 180, 40, "hitl_checker_node", COLOR_BOX_HITL, COLOR_BOX_HITL_TEXT)

    # HITL 结果
    hitl_normal = (850, 650, 160, 35, "正常返回", COLOR_BOX_END, COLOR_BOX_END_TEXT)
    hitl_interrupt = (1100, 650, 160, 35, "interrupt → 等待人工", COLOR_BOX_HITL, COLOR_BOX_HITL_TEXT)

    # END 节点
    end1 = (500, 500, 80, 30, "END", COLOR_BOX_END, COLOR_BOX_END_TEXT)
    end2 = (700, 500, 80, 30, "END", COLOR_BOX_END, COLOR_BOX_END_TEXT)
    end3 = (850, 720, 80, 30, "END", COLOR_BOX_END, COLOR_BOX_END_TEXT)
    end4 = (1100, 720, 80, 30, "END", COLOR_BOX_END, COLOR_BOX_END_TEXT)

    # ==================== 绘制连接线 ====================

    # 用户 → classifier
    draw_arrow(draw, (600, 130), (600, 162))

    # classifier → 前置检测（左侧）
    draw_arrow(draw, (540, 207), (440, 250))

    # classifier → LLM 分类（右侧）
    draw_arrow(draw, (660, 207), (750, 250))

    # 前置检测 → 前置结果
    draw_arrow(draw, (350, 290), (350, 327))

    # 前置结果 → END（隐含）
    draw.text((260, 375), "→ 直接返回", font=font_small, fill=COLOR_DETECT_TEXT if 'COLOR_DETECT_TEXT' in dir() else COLOR_LABEL)

    # LLM 分类 → 意图路由
    draw_arrow(draw, (750, 290), (750, 337))

    # 意图路由 → greeting
    draw_arrow(draw, (710, 373), (530, 417))
    draw.text((580, 390), "greeting", font=font_small, fill=COLOR_LABEL)

    # 意图路由 → unknown
    draw_arrow(draw, (750, 373), (700, 417))
    draw.text((715, 390), "unknown", font=font_small, fill=COLOR_LABEL)

    # 意图路由 → agent_product
    draw_arrow(draw, (800, 373), (900, 417))
    draw.text((830, 390), "product", font=font_small, fill=COLOR_LABEL)

    # 意图路由 → agent_fault
    draw_arrow(draw, (820, 373), (1050, 417))
    draw.text((920, 390), "fault", font=font_small, fill=COLOR_LABEL)

    # 意图路由 → agent_training
    draw_arrow(draw, (830, 373), (1050, 472))
    draw.text((930, 445), "training", font=font_small, fill=COLOR_LABEL)

    # greeting → END
    draw_arrow(draw, (500, 452), (500, 485))

    # unknown → END
    draw_arrow(draw, (700, 452), (700, 485))

    # agent → hitl_checker
    draw_arrow(draw, (975, 452), (975, 550))

    # hitl_checker → 正常返回
    draw_arrow(draw, (920, 590), (890, 632))
    draw.text((865, 610), "不需要人工", font=font_small, fill=COLOR_LABEL)

    # hitl_checker → interrupt
    draw_arrow(draw, (1030, 590), (1100, 632))
    draw.text((1040, 610), "需要人工", font=font_small, fill=COLOR_HITL_TEXT if 'COLOR_HITL_TEXT' in dir() else COLOR_BOX_HITL)

    # 正常返回 → END
    draw_arrow(draw, (850, 667), (850, 705))

    # interrupt → END
    draw_arrow(draw, (1100, 667), (1100, 705))

    # ==================== 绘制节点 ====================

    nodes = [user, classifier, pre_detect, llm_classify, pre_result,
             intent_route, greeting, unknown,
             agent_product, agent_fault, agent_training,
             hitl_checker, hitl_normal, hitl_interrupt,
             end1, end2, end3, end4]

    for (cx, cy, w, h, text, color, text_color) in nodes:
        x1, y1 = cx - w // 2, cy - h // 2
        x2, y2 = cx + w // 2, cy + h // 2
        draw_rounded_rect(draw, (x1, y1, x2, y2), radius=10, fill=color)
        draw_text_center(draw, (cx, cy), text, font_box, text_color)

    # ==================== 图例 ====================
    legend_y = 810
    legend_items = [
        (COLOR_BOX_NORMAL, "正常流程"),
        (COLOR_BOX_DETECT, "前置检测"),
        (COLOR_BOX_AGENT, "Agent 节点"),
        (COLOR_BOX_HITL, "HITL 相关"),
        (COLOR_BOX_END, "终端节点"),
    ]

    legend_x = 250
    for color, label in legend_items:
        draw.rounded_rectangle((legend_x, legend_y, legend_x + 20, legend_y + 16), radius=3, fill=color)
        draw.text((legend_x + 28, legend_y), label, font=font_small, fill=COLOR_LABEL)
        legend_x += 130

    # ==================== 保存 ====================
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "architecture.png")
    img.save(output_path, "PNG", dpi=(150, 150))
    print(f"架构图已保存到：{output_path}")


if __name__ == "__main__":
    main()
