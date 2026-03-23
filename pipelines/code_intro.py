"""代码项目介绍视频 Pipeline

流程：
  [快速分析] → [竞品调研] → [脚本生成]
  → [AI图片 + TTS 并发] → [Remotion 渲染] → MP4

需要 Node.js 环境和 remotion/ 子项目。
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from pipelines.base import BasePipeline, PipelineResult
from modules import script as script_mod
from modules import tts as tts_mod
from modules import composer
from modules import remotion_render
from modules.code_analyzer import ProjectAnalysis, analyze_project
from modules.competitor import research_competitors


class CodeIntroPipeline(BasePipeline):
    name = "code_intro"

    def __init__(
        self,
        output_dir: str | Path = "./output",
        num_scenes: int = 7,
        music_path: str | None = None,
    ):
        super().__init__(output_dir)
        self.num_scenes = num_scenes
        self.music_path = music_path

    async def run(self, topic: str) -> PipelineResult:
        """topic 在此 pipeline 中代表项目路径"""
        project_path = topic
        output_dir = self._ensure_output_dir()

        print(f"\n{'='*50}")
        print(f"[{self.name}] 项目: {project_path}")
        print(f"{'='*50}")

        # 前置检查：确保 Remotion 可用
        remotion_ok = await remotion_render.ensure_remotion_installed()
        if not remotion_ok:
            raise RuntimeError(
                "Remotion 不可用。请确保安装了 Node.js，"
                "并在 remotion/ 目录下运行 npm install。"
            )

        # Stage 1: 代码分析
        print("\n[1/5] 分析项目代码...")
        analysis = await analyze_project(project_path)
        safe = self._safe_name(analysis.name)
        print(f"  项目名: {analysis.name}")
        print(f"  技术栈: {', '.join(analysis.tech_stack[:5])}")
        print(f"  代码量: {analysis.total_loc} 行, {analysis.total_files} 个文件")

        # Stage 2: 竞品调研
        print("\n[2/5] 竞品调研...")
        competitors = await research_competitors(
            analysis.name, analysis.description, analysis.tech_stack,
        )
        if competitors.competitors:
            print(f"  发现 {len(competitors.competitors)} 个竞品")
        if competitors.differentiators:
            print(f"  差异化: {', '.join(competitors.differentiators[:3])}")

        # Stage 3: 脚本生成
        print("\n[3/5] 生成分镜脚本...")
        script = await script_mod.generate_code_intro_script(
            analysis, competitors, output_dir, self.num_scenes,
        )
        print(f"  标题: {script['title']}")
        print(f"  场景数: {len(script['scenes'])}")
        for i, s in enumerate(script["scenes"]):
            print(f"    [{i+1}] {s.get('visual_type', 'ai_image')}: {s['narration'][:30]}...")

        # Stage 4: AI 图片 + TTS 并发
        print("\n[4/5] 并发生成 AI 图片和配音...")
        image_paths, tts_path = await asyncio.gather(
            self._generate_ai_images(script["scenes"], output_dir, safe),
            _generate_tts(script["scenes"], output_dir, safe),
        )

        # Stage 5: Remotion 渲染
        print("\n[5/5] Remotion 渲染视频...")
        audio_duration = await composer.get_audio_duration(tts_path)
        output_path = str(output_dir / f"{safe}_final.mp4")

        await remotion_render.render_with_remotion(
            script, analysis, image_paths, tts_path,
            audio_duration, output_path,
        )

        size_mb = Path(output_path).stat().st_size / 1024 / 1024
        print(f"\n完成！输出: {output_path} ({size_mb:.1f} MB)")
        print(f"   标题: {script['title']}")
        print(f"   标签: {' '.join(script.get('tags', []))}")

        return PipelineResult(
            topic=analysis.name,
            title=script["title"],
            output_path=output_path,
            tags=script.get("tags", []),
            metadata={
                "project_path": project_path,
                "total_loc": analysis.total_loc,
                "tech_stack": analysis.tech_stack,
                "github_url": analysis.github_url,
            },
        )

    async def _generate_ai_images(
        self,
        scenes: list[dict],
        output_dir: Path,
        safe: str,
    ) -> dict[int, str]:
        """只生成 ai_image 类型场景的图片，返回 {场景索引: 图片路径}

        只有 API 调用真正成功的图片才会被纳入结果。
        失败的场景不会写入 result，Remotion 会用 React 组件渲染替代。
        """
        result: dict[int, str] = {}

        async def _one(i: int, scene: dict) -> None:
            vtype = scene.get("visual_type", "ai_image")
            if vtype != "ai_image":
                return
            path = str(output_dir / f"{safe}_img_{i}.jpg")
            try:
                img_bytes = await _generate_ai_image_bytes(scene)
                Path(path).write_bytes(img_bytes)
                result[i] = path
                print(f"  [AI图片 {i+1}] 生成完成")
            except Exception as e:
                print(f"  [AI图片 {i+1}] 失败({e})，Remotion 将用动画场景替代")

        await asyncio.gather(*[_one(i, s) for i, s in enumerate(scenes)])
        total_ai = sum(1 for s in scenes if s.get("visual_type") == "ai_image")
        print(f"  AI 图片: {len(result)}/{total_ai} 张成功")
        return result


async def _generate_ai_image_bytes(scene: dict) -> bytes:
    """调用 MiniMax API 生成图片，返回原始字节。失败直接 raise。"""
    from modules import providers
    from modules.script import QUALITY_SUFFIX

    enhanced = scene["image_prompt"] + QUALITY_SUFFIX
    return await providers.generate_image(enhanced)


async def _generate_tts(scenes: list[dict], output_dir: Path, safe: str) -> str:
    """合并旁白并生成 TTS"""
    from modules import tts as tts_mod

    full_narration = "".join(s["narration"] for s in scenes)
    tts_path = str(output_dir / f"{safe}_tts.mp3")
    print(f"  TTS: {len(full_narration)} 字")
    await tts_mod.synthesize(full_narration, tts_path)
    print(f"  配音完成: {tts_path}")
    return tts_path
