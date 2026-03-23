"""字幕烧录模块 — 用 Pillow 将旁白文字叠加到图片底部"""
from __future__ import annotations

from pathlib import Path

# macOS 中文字体候选（跨平台可扩展此列表）
_FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/Library/Fonts/Arial Unicode MS.ttf",
    # Linux 常见路径
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


def _get_font(size: int):
    from PIL import ImageFont
    for fp in _FONT_CANDIDATES:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def burn_subtitles(
    image_paths: list[str],
    scenes: list[dict],
    output_dir: Path,
    safe: str,
) -> list[str]:
    """
    1. 把原图 resize+crop 到 1080×1920（竖屏）
    2. 在底部绘制旁白字幕（白字+黑描边+半透明背景条）
    返回新图片路径列表。
    """
    from PIL import Image, ImageDraw

    from modules.constants import VIDEO_WIDTH as TARGET_W, VIDEO_HEIGHT as TARGET_H
    font_main = _get_font(52)
    font_size = 52
    line_height = font_size + 14
    max_chars = 14

    captioned = []
    for i, (img_path, scene) in enumerate(zip(image_paths, scenes)):
        img = Image.open(img_path).convert("RGB")

        # 1. Resize+crop 到 1080×1920
        img_w, img_h = img.size
        scale = max(TARGET_W / img_w, TARGET_H / img_h)
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - TARGET_W) // 2
        top = (new_h - TARGET_H) // 2
        img = img.crop((left, top, left + TARGET_W, top + TARGET_H))

        # 2. 字幕绘制
        narration = scene["narration"]
        lines = [narration[j:j + max_chars] for j in range(0, len(narration), max_chars)]
        lines = lines[:4]

        total_text_h = len(lines) * line_height + 20
        bar_top = TARGET_H - total_text_h - 60
        bar_bottom = TARGET_H - 40

        # 半透明黑色背景条
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        bar_draw = ImageDraw.Draw(overlay)
        bar_draw.rectangle([(0, bar_top), (TARGET_W, bar_bottom)], fill=(0, 0, 0, 140))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

        draw = ImageDraw.Draw(img)
        y_start = bar_top + 10

        for li, line in enumerate(lines):
            y = y_start + li * line_height
            bbox = draw.textbbox((0, 0), line, font=font_main)
            tw = bbox[2] - bbox[0]
            x = (TARGET_W - tw) // 2

            # 黑色描边
            for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2),
                            (0, -2), (0, 2), (-2, 0), (2, 0)]:
                draw.text((x + dx, y + dy), line, font=font_main, fill=(0, 0, 0))
            # 白色主字
            draw.text((x, y), line, font=font_main, fill=(255, 255, 255))

        out_path = str(output_dir / f"{safe}_cap_{i}.jpg")
        img.save(out_path, quality=92)
        captioned.append(out_path)

    return captioned
