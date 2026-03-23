"""热点解说视频 Pipeline

流程：
  [生成脚本] → [AI图片 + TTS 并发] → [字幕烧录] → [合成视频]
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from pipelines.base import BasePipeline, PipelineResult
from modules import script as script_mod
from modules import image as image_mod
from modules import tts as tts_mod
from modules import subtitle as subtitle_mod
from modules import composer


class HotTopicPipeline(BasePipeline):
    name = "hot_topic"

    def __init__(self, output_dir: str | Path = "./output", publish: bool = False):
        super().__init__(output_dir)
        self.publish = publish

    async def run(self, topic: str) -> PipelineResult:
        output_dir = self._ensure_output_dir()
        safe = self._safe_name(topic)

        print(f"\n{'='*50}")
        print(f"[{self.name}] 话题: {topic}")
        print(f"{'='*50}")

        # Step 1: 生成分镜脚本
        print("\n[1/4] 生成分镜脚本...")
        script = await script_mod.generate_script(topic, output_dir)
        print(f"  标题: {script['title']}")
        print(f"  场景数: {len(script['scenes'])}")

        # Step 2: 图片 + TTS 并发执行（互相独立）
        print("\n[2/4] 并发生成图片和配音...")
        image_paths, tts_path = await asyncio.gather(
            image_mod.generate_scene_images(script["scenes"], output_dir, safe),
            _generate_tts(script["scenes"], output_dir, safe),
        )

        # Step 3: 字幕烧录（放线程池，避免阻塞 event loop）
        print("\n[3/4] 字幕烧录...")
        loop = asyncio.get_running_loop()
        captioned = await loop.run_in_executor(
            None,
            subtitle_mod.burn_subtitles,
            image_paths, script["scenes"], output_dir, safe,
        )
        print(f"  {len(captioned)} 张字幕烧录完成")

        # Step 4: 合成视频
        print("\n[4/4] 合成视频...")
        output_path = str(output_dir / f"{safe}_final.mp4")
        await composer.images_to_video(captioned, tts_path, output_path)

        size_mb = Path(output_path).stat().st_size / 1024 / 1024
        print(f"\n✅ 完成！输出: {output_path} ({size_mb:.1f} MB)")
        print(f"   标题: {script['title']}")
        print(f"   标签: {' '.join('#' + t for t in script.get('tags', []))}")

        result = PipelineResult(
            topic=topic,
            title=script["title"],
            output_path=output_path,
            tags=script.get("tags", []),
            description=script.get("description", ""),
        )

        # 可选：自动发布到抖音
        if self.publish:
            await _publish_to_douyin(result)

        return result


async def _publish_to_douyin(result: PipelineResult) -> None:
    from modules import douyin_publisher
    print("\n[发布] 上传到抖音...")
    try:
        await douyin_publisher.publish(
            video_path=result.output_path,
            title=result.title,
            tags=result.tags,
            description=result.description,
        )
        print("  ✅ 抖音发布成功！")
    except RuntimeError as exc:
        print(f"  ⚠️  抖音发布失败: {exc}")
    except Exception as exc:
        print(f"  ⚠️  抖音发布异常: {exc}")


async def _generate_tts(scenes: list[dict], output_dir: Path, safe: str) -> str:
    full_narration = "".join(s["narration"] for s in scenes)
    tts_path = str(output_dir / f"{safe}_tts.mp3")
    print(f"  TTS: {len(full_narration)} 字")
    await tts_mod.synthesize(full_narration, tts_path)
    print(f"  配音完成: {tts_path}")
    return tts_path
