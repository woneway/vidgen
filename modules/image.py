"""AI 图片生成模块 — 并发生成场景图片，失败自动降级为文字卡片"""
from __future__ import annotations

import asyncio
from pathlib import Path

from modules import providers, card
from modules.script import QUALITY_SUFFIX


async def generate_scene_images(
    scenes: list[dict],
    output_dir: Path,
    safe_name: str,
) -> list[str]:
    """
    并发生成所有场景图片。
    单张失败时降级为本地文字卡片，不中断整体流程。
    """
    async def _one(i: int, scene: dict) -> str:
        path = str(output_dir / f"{safe_name}_img_{i}.jpg")
        enhanced_prompt = scene["image_prompt"] + QUALITY_SUFFIX
        try:
            img_bytes = await providers.generate_image(enhanced_prompt)
            Path(path).write_bytes(img_bytes)
            print(f"  [图片 {i+1}/{len(scenes)}] AI 图片生成完成")
        except Exception as e:
            print(f"  [图片 {i+1}/{len(scenes)}] AI 图片失败({e})，降级文字卡片")
            path = await card.make_card(scene["narration"][:40], path, i)
        return path

    return list(await asyncio.gather(*[_one(i, s) for i, s in enumerate(scenes)]))
