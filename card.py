"""本地生成文字卡片图片 - 用 ffmpeg drawtext，零外部依赖"""
import asyncio
import textwrap
from pathlib import Path

# 渐变色方案（每个场景换一个）
GRADIENTS = [
    ("1a1a2e", "16213e"),   # 深蓝
    ("0f3460", "533483"),   # 蓝紫
    ("1b1b2f", "e94560"),   # 深蓝红
    ("162447", "1f4068"),   # 深蓝
    ("1a1a2e", "e94560"),   # 深蓝玫红
]


async def make_card(text: str, output_path: str, index: int = 0) -> str:
    """
    生成 608x1080 文字卡片
    - 渐变背景
    - 居中文字，自动换行
    """
    color1, color2 = GRADIENTS[index % len(GRADIENTS)]

    # 文字换行处理（每行最多14个字）
    lines = textwrap.wrap(text, width=14)
    # ffmpeg drawtext 不支持换行，用多个 drawtext 叠加
    y_start = 400
    line_height = 80

    # 构建 drawtext filter（每行一个）
    dt_filters = []
    for i, line in enumerate(lines[:6]):  # 最多6行
        y = y_start + i * line_height
        # 转义特殊字符
        safe = line.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")
        dt_filters.append(
            f"drawtext=text='{safe}':fontcolor=white:fontsize=52:"
            f"x=(w-text_w)/2:y={y}:font='PingFang SC'"
        )

    filter_str = ",".join(dt_filters) if dt_filters else "null"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=0x{color1}:size=608x1080:rate=1",
        "-vf", filter_str,
        "-frames:v", "1",
        output_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        # 降级：纯色背景不加文字
        await _plain_card(color1, output_path)

    return output_path


async def _plain_card(color: str, output_path: str):
    """降级方案：纯色背景"""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=0x{color}:size=608x1080:rate=1",
        "-frames:v", "1",
        output_path,
    ]
    proc = await asyncio.create_subprocess_exec(*cmd,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await proc.communicate()


async def make_cards(scenes: list[dict], output_dir: str) -> list[str]:
    """批量生成所有场景卡片，返回图片路径列表"""
    tasks = [
        make_card(scene["narration"][:40], f"{output_dir}/card_{i}.png", i)
        for i, scene in enumerate(scenes)
    ]
    return await asyncio.gather(*tasks)
