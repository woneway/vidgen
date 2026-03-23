"""视频生成主流水线 - 图片轮播版"""
import asyncio
from pathlib import Path
from dataclasses import dataclass

import minimax
import merger
import tts as tts_module
import card as card_module
from modules.script import parse_script_json

SCRIPT_SYSTEM = """你是短视频脚本创作专家，擅长热点解说类内容。

根据给定话题，生成一个 30~50 秒的图文解说视频脚本，包含：
- 5 个画面场景，每个场景有图片描述（英文，画面感强，适合 AI 生图）和对应旁白（中文，口语化）
- 整体旁白加起来约 150~200 字

严格输出 JSON，格式如下：
{
  "title": "视频标题（20字以内，吸引眼球）",
  "scenes": [
    {"image_prompt": "...", "narration": "..."},
    {"image_prompt": "...", "narration": "..."},
    {"image_prompt": "...", "narration": "..."},
    {"image_prompt": "...", "narration": "..."},
    {"image_prompt": "...", "narration": "..."}
  ],
  "tags": ["话题标签1", "话题标签2", "话题标签3"]
}"""


async def _generate_images(scenes: list[dict], output_dir: str, safe_name: str) -> list[str]:
    """并发生成所有场景图片，单张失败降级为本地文字卡片"""
    async def _one(i: int, scene: dict) -> str:
        path = f"{output_dir}/{safe_name}_img_{i}.jpg"
        try:
            img_bytes = await minimax.generate_image(scene["image_prompt"])
            Path(path).write_bytes(img_bytes)
            print(f"  [{i+1}] ✅ AI图片")
        except Exception as e:
            print(f"  [{i+1}] ⚠️  AI图片失败({e})，降级文字卡片")
            path = await card_module.make_card(scene["narration"][:40], path, i)
        return path

    return list(await asyncio.gather(*[_one(i, s) for i, s in enumerate(scenes)]))


@dataclass
class PipelineResult:
    topic: str
    title: str
    output_path: str
    tags: list[str]


async def run(topic: str, output_dir: str = "./output") -> PipelineResult:
    Path(output_dir).mkdir(exist_ok=True)
    safe_name = topic[:20].replace(" ", "_").replace("/", "_")

    print(f"\n{'='*50}")
    print(f"话题: {topic}")
    print(f"{'='*50}")

    # Step 1: 生成脚本
    print("\n[1/4] 生成分镜脚本...")
    raw = await minimax.chat(f"话题：{topic}", system=SCRIPT_SYSTEM)
    script = parse_script_json(raw)
    print(f"  标题: {script['title']}")
    print(f"  场景数: {len(script['scenes'])}")

    # Step 2: AI 图片生成（失败自动降级为本地文字卡片）
    print("\n[2/4] 生成场景图片（MiniMax 文生图）...")
    image_paths = await _generate_images(script["scenes"], output_dir, safe_name)
    print(f"  ✅ {len(image_paths)} 张图片生成完成")

    # Step 3: 合成 TTS（拼接所有场景旁白）
    print("\n[3/4] 生成配音（edge-tts，免费）...")
    full_narration = "".join(
        scene["narration"] for scene in script["scenes"]
    )
    tts_path = f"{output_dir}/{safe_name}_tts.mp3"
    await tts_module.synthesize(full_narration, tts_path)
    print(f"  ✅ 配音已生成: {tts_path}")

    # Step 4: ffmpeg 合成
    print("\n[4/4] 合成视频...")
    output_path = f"{output_dir}/{safe_name}_final.mp4"
    await merger.images_to_video(image_paths, tts_path, output_path)

    size_mb = Path(output_path).stat().st_size / 1024 / 1024
    print(f"\n✅ 完成！输出: {output_path} ({size_mb:.1f} MB)")
    print(f"   标题: {script['title']}")
    print(f"   标签: {' '.join('#'+t for t in script.get('tags', []))}")

    return PipelineResult(
        topic=topic,
        title=script["title"],
        output_path=output_path,
        tags=script.get("tags", []),
    )
