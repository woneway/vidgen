"""可视化卡片模块 — 标题卡、结尾卡、代码卡、数据卡、架构卡

所有卡片统一 1080×1920，使用 Pillow 渲染，深色主题。
"""
from __future__ import annotations

import asyncio
import textwrap
from pathlib import Path

from modules.constants import VIDEO_WIDTH, VIDEO_HEIGHT

# 深色主题配色
BG_DARK = (13, 17, 23)        # #0d1117 GitHub Dark
BG_CARD = (22, 27, 34)        # #161b22 卡片背景
ACCENT_BLUE = (56, 132, 244)  # #3884f4 强调色
ACCENT_GREEN = (63, 185, 80)  # #3fb950
ACCENT_ORANGE = (210, 153, 34)  # #d29922
TEXT_WHITE = (230, 237, 243)   # #e6edf3
TEXT_GRAY = (139, 148, 158)    # #8b949e
TEXT_BRIGHT = (255, 255, 255)

# macOS 中文字体候选
_FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/Library/Fonts/Arial Unicode MS.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

_MONO_FONT_CANDIDATES = [
    "/System/Library/Fonts/SFMono-Regular.otf",
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Monaco.dfont",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
]


def _get_font(size: int, mono: bool = False):
    from PIL import ImageFont
    candidates = _MONO_FONT_CANDIDATES if mono else _FONT_CANDIDATES
    for fp in candidates:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    # 回退：非等宽也试试
    if mono:
        return _get_font(size, mono=False)
    return ImageFont.load_default()


def _draw_rounded_rect(draw, xy, radius, fill):
    """绘制圆角矩形"""
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.pieslice([x0, y0, x0 + 2 * radius, y0 + 2 * radius], 180, 270, fill=fill)
    draw.pieslice([x1 - 2 * radius, y0, x1, y0 + 2 * radius], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2 * radius, x0 + 2 * radius, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2 * radius, y1 - 2 * radius, x1, y1], 0, 90, fill=fill)


def _draw_gradient_bg(img):
    """在图片上绘制深色渐变背景"""
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    # 从深蓝到更深蓝的竖向渐变
    for y in range(VIDEO_HEIGHT):
        ratio = y / VIDEO_HEIGHT
        r = int(13 + ratio * 10)
        g = int(17 + ratio * 5)
        b = int(23 + ratio * 15)
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(r, g, b))


async def make_title_card(
    project_name: str,
    tagline: str,
    output_path: str,
) -> str:
    """标题卡：项目名（大字）+ 标语（小字）+ 渐变背景"""
    from PIL import Image, ImageDraw

    loop = asyncio.get_running_loop()

    def _render():
        img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_DARK)
        _draw_gradient_bg(img)
        draw = ImageDraw.Draw(img)

        # 装饰线
        line_y = 700
        draw.rectangle([(340, line_y), (740, line_y + 4)], fill=ACCENT_BLUE)

        # 项目名（大字）
        font_name = _get_font(96)
        bbox = draw.textbbox((0, 0), project_name, font=font_name)
        tw = bbox[2] - bbox[0]
        x = (VIDEO_WIDTH - tw) // 2
        draw.text((x, 750), project_name, font=font_name, fill=TEXT_BRIGHT)

        # 标语（小字，多行）
        font_tag = _get_font(42)
        tag_lines = textwrap.wrap(tagline, width=20)
        y = 900
        for line in tag_lines[:3]:
            bbox = draw.textbbox((0, 0), line, font=font_tag)
            tw = bbox[2] - bbox[0]
            x = (VIDEO_WIDTH - tw) // 2
            draw.text((x, y), line, font=font_tag, fill=TEXT_GRAY)
            y += 60

        # 底部装饰
        draw.rectangle([(440, 1100), (640, 1104)], fill=ACCENT_GREEN)

        img.save(output_path, quality=95)

    await loop.run_in_executor(None, _render)
    return output_path


async def make_ending_card(
    project_name: str,
    github_url: str | None,
    summary: str,
    output_path: str,
) -> str:
    """结尾卡：项目名 + GitHub URL + 总结 + CTA"""
    from PIL import Image, ImageDraw

    loop = asyncio.get_running_loop()

    def _render():
        img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_DARK)
        _draw_gradient_bg(img)
        draw = ImageDraw.Draw(img)

        # 项目名
        font_name = _get_font(80)
        bbox = draw.textbbox((0, 0), project_name, font=font_name)
        tw = bbox[2] - bbox[0]
        draw.text(((VIDEO_WIDTH - tw) // 2, 650), project_name, font=font_name, fill=TEXT_BRIGHT)

        # 总结
        font_summary = _get_font(38)
        summary_lines = textwrap.wrap(summary, width=22)
        y = 800
        for line in summary_lines[:4]:
            bbox = draw.textbbox((0, 0), line, font=font_summary)
            tw = bbox[2] - bbox[0]
            draw.text(((VIDEO_WIDTH - tw) // 2, y), line, font=font_summary, fill=TEXT_GRAY)
            y += 56

        # GitHub URL
        if github_url:
            font_url = _get_font(32)
            short_url = github_url.replace("https://", "")
            bbox = draw.textbbox((0, 0), short_url, font=font_url)
            tw = bbox[2] - bbox[0]
            draw.text(((VIDEO_WIDTH - tw) // 2, y + 40), short_url, font=font_url, fill=ACCENT_BLUE)
            y += 100

        # CTA 按钮样式
        cta_text = "Star on GitHub"
        font_cta = _get_font(44)
        bbox = draw.textbbox((0, 0), cta_text, font=font_cta)
        cta_w = bbox[2] - bbox[0] + 80
        cta_h = bbox[3] - bbox[1] + 40
        cta_x = (VIDEO_WIDTH - cta_w) // 2
        cta_y = y + 60
        _draw_rounded_rect(draw, (cta_x, cta_y, cta_x + cta_w, cta_y + cta_h), 12, ACCENT_BLUE)
        bbox = draw.textbbox((0, 0), cta_text, font=font_cta)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (cta_x + (cta_w - tw) // 2, cta_y + (cta_h - th) // 2 - 4),
            cta_text, font=font_cta, fill=TEXT_BRIGHT,
        )

        img.save(output_path, quality=95)

    await loop.run_in_executor(None, _render)
    return output_path


async def make_code_card(
    example: dict,
    output_path: str,
) -> str:
    """代码卡片：语法高亮代码 + 文件名标题

    example: {filename, code, language}
    """
    from PIL import Image, ImageDraw

    loop = asyncio.get_running_loop()

    def _render():
        img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_DARK)
        _draw_gradient_bg(img)
        draw = ImageDraw.Draw(img)

        filename = example.get("filename", "code")
        code = example.get("code", "")
        language = example.get("language", "")

        # 代码区域背景
        code_margin = 60
        code_top = 400
        code_bottom = 1500
        _draw_rounded_rect(
            draw,
            (code_margin, code_top, VIDEO_WIDTH - code_margin, code_bottom),
            16, BG_CARD,
        )

        # 标题栏（文件名 + 语言标签）
        header_h = 60
        _draw_rounded_rect(
            draw,
            (code_margin, code_top, VIDEO_WIDTH - code_margin, code_top + header_h),
            16, (30, 36, 44),
        )
        # 填充标题栏底部的圆角
        draw.rectangle(
            [code_margin, code_top + header_h - 16, VIDEO_WIDTH - code_margin, code_top + header_h],
            fill=(30, 36, 44),
        )

        # 窗口按钮
        for i, color in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            cx = code_margin + 30 + i * 28
            cy = code_top + header_h // 2
            draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=color)

        # 文件名
        font_header = _get_font(26)
        draw.text(
            (code_margin + 120, code_top + 16),
            filename, font=font_header, fill=TEXT_GRAY,
        )

        # 语言标签
        if language:
            font_lang = _get_font(22)
            lang_text = language.upper()
            bbox = draw.textbbox((0, 0), lang_text, font=font_lang)
            tw = bbox[2] - bbox[0]
            draw.text(
                (VIDEO_WIDTH - code_margin - tw - 20, code_top + 18),
                lang_text, font=font_lang, fill=ACCENT_ORANGE,
            )

        # 代码内容 — 使用 Pygments 语法高亮
        _draw_highlighted_code(draw, code, language, code_margin + 30, code_top + header_h + 20)

        img.save(output_path, quality=95)

    await loop.run_in_executor(None, _render)
    return output_path


def _draw_highlighted_code(draw, code: str, language: str, x_start: int, y_start: int):
    """用 Pygments 对代码进行语法高亮并绘制到图片"""
    try:
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name, TextLexer
        from pygments.token import Token

        try:
            lexer = get_lexer_by_name(language)
        except Exception:
            lexer = TextLexer()

        # Monokai 风格的配色
        token_colors = {
            Token.Keyword: (249, 38, 114),       # 粉红
            Token.Keyword.Namespace: (249, 38, 114),
            Token.Name.Function: (166, 226, 46),  # 绿色
            Token.Name.Class: (166, 226, 46),
            Token.Name.Decorator: (166, 226, 46),
            Token.Literal.String: (230, 219, 116),  # 黄色
            Token.Literal.String.Doc: (230, 219, 116),
            Token.Literal.Number: (174, 129, 255),  # 紫色
            Token.Comment: (117, 113, 94),         # 灰色
            Token.Comment.Single: (117, 113, 94),
            Token.Operator: (249, 38, 114),
            Token.Punctuation: TEXT_GRAY,
            Token.Name.Builtin: (102, 217, 239),  # 青色
        }

        font_code = _get_font(28, mono=True)
        line_height = 38

        # 行号宽度
        lines = code.split("\n")
        num_width = len(str(len(lines))) * 18 + 10

        tokens = list(lexer.get_tokens(code))
        current_x = x_start + num_width
        current_y = y_start
        line_num = 1
        max_y = y_start + 1000  # 防止超出代码区域

        # 画行号
        font_linenum = _get_font(24, mono=True)
        draw.text((x_start, current_y), str(line_num), font=font_linenum, fill=TEXT_GRAY)

        for ttype, value in tokens:
            if current_y > max_y:
                break

            # 查找 token 颜色
            color = TEXT_WHITE
            t = ttype
            while t:
                if t in token_colors:
                    color = token_colors[t]
                    break
                t = t.parent

            for char in value:
                if char == "\n":
                    current_x = x_start + num_width
                    current_y += line_height
                    line_num += 1
                    if current_y > max_y:
                        break
                    draw.text((x_start, current_y), str(line_num), font=font_linenum, fill=TEXT_GRAY)
                else:
                    draw.text((current_x, current_y), char, font=font_code, fill=color)
                    bbox = draw.textbbox((0, 0), char, font=font_code)
                    current_x += bbox[2] - bbox[0]

    except ImportError:
        # Pygments 不可用，直接白色绘制
        font_code = _get_font(28, mono=True)
        line_height = 38
        y = y_start
        for line in code.split("\n")[:25]:
            if y > y_start + 1000:
                break
            draw.text((x_start, y), line[:50], font=font_code, fill=TEXT_WHITE)
            y += line_height


async def make_data_card(
    analysis,  # ProjectAnalysis
    output_path: str,
) -> str:
    """数据可视化卡片：LOC、文件数、依赖数等指标，2×2 网格布局"""
    from PIL import Image, ImageDraw

    loop = asyncio.get_running_loop()

    def _render():
        img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_DARK)
        _draw_gradient_bg(img)
        draw = ImageDraw.Draw(img)

        # 标题
        font_title = _get_font(56)
        title_text = "项目数据一览"
        bbox = draw.textbbox((0, 0), title_text, font=font_title)
        tw = bbox[2] - bbox[0]
        draw.text(((VIDEO_WIDTH - tw) // 2, 350), title_text, font=font_title, fill=TEXT_BRIGHT)

        # 装饰线
        draw.rectangle([(380, 430), (700, 434)], fill=ACCENT_BLUE)

        # 数据项
        metrics = [
            (_format_number(analysis.total_loc), "代码行数", ACCENT_BLUE),
            (str(analysis.total_files), "源文件数", ACCENT_GREEN),
            (str(len(analysis.dependencies)), "依赖数量", ACCENT_ORANGE),
            (str(len(analysis.tech_stack)), "技术栈", (174, 129, 255)),  # 紫色
        ]

        # 2×2 网格
        card_w, card_h = 420, 280
        gap = 60
        start_x = (VIDEO_WIDTH - 2 * card_w - gap) // 2
        start_y = 520

        font_num = _get_font(72)
        font_label = _get_font(32)

        for idx, (value, label, color) in enumerate(metrics):
            col = idx % 2
            row = idx // 2
            cx = start_x + col * (card_w + gap)
            cy = start_y + row * (card_h + gap)

            # 卡片背景
            _draw_rounded_rect(draw, (cx, cy, cx + card_w, cy + card_h), 16, BG_CARD)

            # 顶部色条
            _draw_rounded_rect(draw, (cx, cy, cx + card_w, cy + 6), 3, color)

            # 数值
            bbox = draw.textbbox((0, 0), value, font=font_num)
            tw = bbox[2] - bbox[0]
            draw.text(
                (cx + (card_w - tw) // 2, cy + 60),
                value, font=font_num, fill=color,
            )

            # 标签
            bbox = draw.textbbox((0, 0), label, font=font_label)
            tw = bbox[2] - bbox[0]
            draw.text(
                (cx + (card_w - tw) // 2, cy + 180),
                label, font=font_label, fill=TEXT_GRAY,
            )

        # 底部技术栈列表
        if analysis.tech_stack:
            y_tech = start_y + 2 * (card_h + gap) + 40
            font_tech = _get_font(30)
            tech_text = " · ".join(analysis.tech_stack[:6])
            bbox = draw.textbbox((0, 0), tech_text, font=font_tech)
            tw = bbox[2] - bbox[0]
            draw.text(
                ((VIDEO_WIDTH - tw) // 2, y_tech),
                tech_text, font=font_tech, fill=TEXT_GRAY,
            )

        img.save(output_path, quality=95)

    await loop.run_in_executor(None, _render)
    return output_path


async def make_architecture_card(
    structure: str,
    output_path: str,
) -> str:
    """架构图卡片：目录树"""
    from PIL import Image, ImageDraw

    loop = asyncio.get_running_loop()

    def _render():
        img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_DARK)
        _draw_gradient_bg(img)
        draw = ImageDraw.Draw(img)

        # 标题
        font_title = _get_font(52)
        title_text = "项目结构"
        bbox = draw.textbbox((0, 0), title_text, font=font_title)
        tw = bbox[2] - bbox[0]
        draw.text(((VIDEO_WIDTH - tw) // 2, 300), title_text, font=font_title, fill=TEXT_BRIGHT)

        # 装饰线
        draw.rectangle([(380, 380), (700, 384)], fill=ACCENT_GREEN)

        # 目录树背景
        tree_margin = 80
        tree_top = 430
        tree_bottom = 1600
        _draw_rounded_rect(
            draw,
            (tree_margin, tree_top, VIDEO_WIDTH - tree_margin, tree_bottom),
            12, BG_CARD,
        )

        # 目录树内容
        font_tree = _get_font(26, mono=True)
        lines = structure.split("\n")
        y = tree_top + 30
        line_h = 34

        for line in lines[:30]:
            if y > tree_bottom - 40:
                draw.text((tree_margin + 20, y), "...", font=font_tree, fill=TEXT_GRAY)
                break

            # 目录用蓝色，文件用白色
            color = ACCENT_BLUE if line.rstrip().endswith("/") else TEXT_WHITE
            # 树形符号用灰色
            stripped = line.lstrip("│├└── ")
            prefix = line[:len(line) - len(line.lstrip("│├└── \t"))]

            if prefix:
                draw.text((tree_margin + 20, y), prefix, font=font_tree, fill=TEXT_GRAY)
            prefix_w = draw.textbbox((0, 0), prefix, font=font_tree)[2] if prefix else 0
            draw.text((tree_margin + 20 + prefix_w, y), stripped, font=font_tree, fill=color)
            y += line_h

        img.save(output_path, quality=95)

    await loop.run_in_executor(None, _render)
    return output_path


def _format_number(n: int) -> str:
    """格式化大数字：1234 → 1.2K, 12345 → 12.3K"""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)
