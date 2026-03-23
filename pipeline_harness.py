"""pipeline_harness.py — 短视频自动生成 Harness 流水线

pipeline:
  FunctionTask [generate_script]        — MiniMax Chat，生成5场景初稿 → dict
      ↓
  Dialogue [script_review]              — Claude 双角色审核迭代，最多2轮 → DialogueOutput
      ↓
  FunctionTask [extract_approved_script] — 从 Dialogue 输出提取最终 JSON → dict
      ↓
  Parallel([
    FunctionTask [generate_images]      — MiniMax 文生图×5 → list[str] 路径
    FunctionTask [generate_tts]         — edge-tts 配音 → str 音频路径
  ])
      ↓
  FunctionTask [merge_with_subs]        — ffmpeg 合成 + Pillow 字幕 → str 视频路径

运行:
    source venv/bin/activate
    MINIMAX_API_KEY=xxx python pipeline_harness.py "DeepSeek最新发布" [--output ./output]
"""
from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import json
import os
import sys
from pathlib import Path

from harness import Dialogue, FunctionTask, Harness, Parallel, Role
from harness._internal.dialogue import DialogueContext

sys.path.insert(0, str(Path(__file__).parent))
import minimax
import card as card_module
import tts as tts_module
from modules.script import parse_script_json, validate_script
from modules.providers import validate_api_key

# ---------------------------------------------------------------------------
# 图片 prompt 质量增强
# ---------------------------------------------------------------------------

QUALITY_SUFFIX = (
    ", cinematic, high quality, 4K, professional photography, "
    "dramatic lighting, detailed, sharp focus, vertical composition"
)

SCRIPT_SYSTEM = """你是短视频脚本创作专家，擅长热点解说类内容。

根据给定话题，生成一个 30~50 秒的图文解说视频脚本，包含：
- 5 个画面场景，每个场景有图片描述（英文，画面感强，适合 AI 生图）和对应旁白（中文，口语化）
- 整体旁白加起来约 150~200 字
- 图片描述不要包含文字、字母、标牌等文本元素

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


# ---------------------------------------------------------------------------
# 工具：在独立线程中运行 async 函数（FunctionTask 是同步的）
# ---------------------------------------------------------------------------

def run_async(coro):
    """在新线程+新事件循环中运行协程，兼容已有事件循环。"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


# ---------------------------------------------------------------------------
# Task 0：生成初稿脚本（MiniMax）
# ---------------------------------------------------------------------------

def make_generate_script(topic: str, output_dir: Path):
    def generate_script(results: list) -> dict:
        print(f"\n[Script] 生成分镜初稿: {topic}")
        script_raw = run_async(
            minimax.chat(f"话题：{topic}", system=SCRIPT_SYSTEM)
        )
        script = parse_script_json(script_raw)
        validate_script(script)
        print(f"  ✅ 初稿标题: {script['title']}  场景数: {len(script['scenes'])}")

        safe = topic[:20].replace(" ", "_").replace("/", "_")
        (output_dir / f"{safe}_script_draft.json").write_text(
            json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return script
    return generate_script


# ---------------------------------------------------------------------------
# Task 1：Dialogue 脚本审核（Claude 双角色）
# ---------------------------------------------------------------------------

def make_script_review_dialogue(topic: str) -> Dialogue:
    """
    双角色审核 Dialogue：
      scriptwriter — 根据初稿或审核意见输出改进版 JSON
      reviewer     — 评审脚本质量，通过时说「审核通过」

    Role.prompt 通过 ctx.pipeline_results[0].output 访问 Task 0 的初稿。
    """

    def scriptwriter_prompt(ctx: DialogueContext) -> str:
        if ctx.round == 0:
            draft = ctx.pipeline_results[0].output
            draft_json = json.dumps(draft, ensure_ascii=False, indent=2)
            return (
                f"以下是 AI 生成的初稿脚本：\n\n{draft_json}\n\n"
                "请审查并优化此脚本，重点改进：\n"
                "1. image_prompt：更强的电影感英文描述，不含文字/标牌/logo\n"
                "2. narration：更自然的中文口语，每条 30~50 字\n"
                "3. title：更吸引眼球的标题\n\n"
                "直接输出完整的改进版 JSON，不需要额外说明。"
            )

        reviewer_last = ctx.last_from("reviewer") or ""
        return (
            f"审核意见：\n{reviewer_last}\n\n"
            "请根据以上意见修改脚本，直接输出完整的改进版 JSON。"
        )

    def reviewer_prompt(ctx: DialogueContext) -> str:
        writer_last = ctx.last_from("scriptwriter") or ""
        return (
            f"请审核以下短视频脚本：\n\n{writer_last}\n\n"
            "评审标准：\n"
            "1. image_prompt 是否有画面感、无文字元素、适合 AI 生图？\n"
            "2. narration 是否口语化、流畅、每条约 30~50 字？\n"
            f"3. 5 个场景是否连贯，整体是否符合话题「{topic}」？\n\n"
            "如果脚本质量符合标准，回复「审核通过」并在后面附上完整 JSON。\n"
            "否则，列出不超过 3 条具体修改意见。"
        )

    return Dialogue(
        background=f"你正在协作完善一个关于「{topic}」的短视频脚本。",
        max_rounds=2,
        until=lambda ctx: "审核通过" in (ctx.last_from("reviewer") or ""),
        roles=[
            Role(
                name="scriptwriter",
                system_prompt=(
                    "你是专业的短视频脚本创作者，擅长热点内容解说。"
                    "你的输出必须是严格的 JSON 格式，遵循 "
                    "{title, scenes[{image_prompt, narration}], tags} 结构，不输出任何额外内容。"
                ),
                prompt=scriptwriter_prompt,
            ),
            Role(
                name="reviewer",
                system_prompt=(
                    "你是短视频内容审核专家，专注于脚本质量评估。"
                    "审核通过时，在回复开头写「审核通过」，然后附上完整 JSON。"
                ),
                prompt=reviewer_prompt,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Task 2：提取 Dialogue 审核后的最终脚本
# ---------------------------------------------------------------------------

def make_extract_approved_script(topic: str, output_dir: Path):
    def extract_approved_script(results: list) -> dict:
        dialogue_output = results[1].output  # DialogueOutput

        # 取脚本创作者的最后一次输出（审核通过的版本）
        writer_turns = [t for t in dialogue_output.turns if t.role_name == "scriptwriter"]

        if writer_turns:
            try:
                script = parse_script_json(writer_turns[-1].content)
                validate_script(script)
                print(
                    f"  ✅ 脚本审核完成 | {dialogue_output.rounds_completed} 轮 "
                    f"| {dialogue_output.total_turns} 次发言"
                )
                safe = topic[:20].replace(" ", "_").replace("/", "_")
                (output_dir / f"{safe}_script_approved.json").write_text(
                    json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                return script
            except Exception as e:
                print(f"  ⚠️  Dialogue 输出解析失败({e})，回退到初稿")

        # 降级：使用 Task 0 的初稿
        print("  ⚠️  使用初稿脚本（Dialogue 未产出有效 JSON）")
        return results[0].output

    return extract_approved_script


# ---------------------------------------------------------------------------
# Task 3.0：图片生成（读 results[2] 即最终脚本）
# ---------------------------------------------------------------------------

def make_generate_images(topic: str, output_dir: Path):
    def generate_images(results: list) -> list[str]:
        script: dict = results[2].output  # Task 2: 最终审核脚本
        scenes = script["scenes"]
        safe = topic[:20].replace(" ", "_").replace("/", "_")

        async def _gen_all():
            async def _one(i: int, scene: dict) -> str:
                path = str(output_dir / f"{safe}_img_{i}.jpg")
                enhanced_prompt = scene["image_prompt"] + QUALITY_SUFFIX
                try:
                    img_bytes = await minimax.generate_image(enhanced_prompt)
                    Path(path).write_bytes(img_bytes)
                    print(f"  [Img {i+1}/5] ✅ AI图片生成完成")
                except Exception as e:
                    print(f"  [Img {i+1}/5] ⚠️  AI图片失败({e})，降级文字卡片")
                    await card_module.make_card(scene["narration"][:40], path, i)
                return path

            return list(await asyncio.gather(*[_one(i, s) for i, s in enumerate(scenes)]))

        print(f"\n[Images] 并发生成 {len(scenes)} 张 AI 图片...")
        paths = run_async(_gen_all())
        print(f"  ✅ {len(paths)} 张图片完成")
        return paths
    return generate_images


# ---------------------------------------------------------------------------
# Task 3.1：TTS 配音（读 results[2] 即最终脚本）
# ---------------------------------------------------------------------------

def make_generate_tts(topic: str, output_dir: Path):
    def generate_tts(results: list) -> str:
        script: dict = results[2].output  # Task 2: 最终审核脚本
        safe = topic[:20].replace(" ", "_").replace("/", "_")
        tts_path = str(output_dir / f"{safe}_tts.mp3")

        full_narration = "".join(s["narration"] for s in script["scenes"])
        print(f"\n[TTS] 生成配音，共 {len(full_narration)} 字...")
        run_async(tts_module.synthesize(full_narration, tts_path))
        print(f"  ✅ 配音: {tts_path}")
        return tts_path
    return generate_tts


# ---------------------------------------------------------------------------
# Task 4：字幕烧录 + ffmpeg 合成（读 results[2/3/4]）
# ---------------------------------------------------------------------------

def make_merge_with_subs(topic: str, output_dir: Path):
    def merge_with_subs(results: list) -> str:
        # results 布局：[draft(0), dialogue(1), script(2), images(3.0→3), tts(3.1→4)]
        script: dict = results[2].output
        image_paths: list[str] = results[3].output
        tts_path: str = results[4].output
        scenes = script["scenes"]
        safe = topic[:20].replace(" ", "_").replace("/", "_")
        output_path = str(output_dir / f"{safe}_final.mp4")

        print(f"\n[Merge] 字幕烧录 + 合成视频...")

        captioned_paths = _burn_subtitles(image_paths, scenes, output_dir, safe)
        print(f"  ✅ {len(captioned_paths)} 张字幕烧录完成")

        async def _merge():
            probe = await asyncio.create_subprocess_exec(
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", tts_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, _ = await probe.communicate()
            duration = float(json.loads(out)["format"]["duration"])
            per_scene = duration / len(scenes)

            n = len(captioned_paths)
            inputs = []
            for p in captioned_paths:
                inputs += ["-loop", "1", "-t", str(per_scene), "-i", p]

            filter_parts = []
            for i in range(n):
                filter_parts.append(
                    f"[{i}:v]fps=25,setpts=PTS-STARTPTS[v{i}]"
                )

            concat_in = "".join(f"[v{i}]" for i in range(n))
            filter_parts.append(f"{concat_in}concat=n={n}:v=1:a=0[vout]")
            filter_complex = ";".join(filter_parts)

            cmd = [
                "ffmpeg", "-y",
                *inputs,
                "-i", tts_path,
                "-filter_complex", filter_complex,
                "-map", "[vout]", "-map", f"{n}:a",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest", "-r", "25",
                output_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"ffmpeg 失败:\n{stderr.decode()[-800:]}")

        run_async(_merge())

        size_mb = Path(output_path).stat().st_size / 1024 / 1024
        print(f"  ✅ 视频: {output_path} ({size_mb:.1f} MB)")
        print(f"  标题: {script['title']}")
        print(f"  标签: {' '.join('#'+t for t in script.get('tags', []))}")
        return output_path

    return merge_with_subs


# ---------------------------------------------------------------------------
# Pillow 字幕烧录
# ---------------------------------------------------------------------------

_FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/Library/Fonts/Arial Unicode MS.ttf",
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


def _burn_subtitles(
    image_paths: list[str],
    scenes: list[dict],
    output_dir: Path,
    safe: str,
) -> list[str]:
    from PIL import Image, ImageDraw
    from modules.constants import VIDEO_WIDTH as TARGET_W, VIDEO_HEIGHT as TARGET_H

    font_main = _get_font(52)
    font_size = 52
    line_height = font_size + 14
    max_chars = 14

    captioned = []
    for i, (img_path, scene) in enumerate(zip(image_paths, scenes)):
        img = Image.open(img_path).convert("RGB")

        img_w, img_h = img.size
        scale = max(TARGET_W / img_w, TARGET_H / img_h)
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - TARGET_W) // 2
        top = (new_h - TARGET_H) // 2
        img = img.crop((left, top, left + TARGET_W, top + TARGET_H))

        narration = scene["narration"]
        lines = [narration[j:j + max_chars] for j in range(0, len(narration), max_chars)]
        lines = lines[:4]

        total_text_h = len(lines) * line_height + 20
        bar_top = TARGET_H - total_text_h - 60
        bar_bottom = TARGET_H - 40

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

            for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2),
                            (0, -2), (0, 2), (-2, 0), (2, 0)]:
                draw.text((x + dx, y + dy), line, font=font_main, fill=(0, 0, 0))
            draw.text((x, y), line, font=font_main, fill=(255, 255, 255))

        out_path = str(output_dir / f"{safe}_cap_{i}.jpg")
        img.save(out_path, quality=92)
        captioned.append(out_path)

    return captioned


# ---------------------------------------------------------------------------
# Pipeline 入口
# ---------------------------------------------------------------------------

async def run(topic: str, output_dir: Path) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)

    h = Harness(
        project_path=str(Path(__file__).parent),
        stream_callback=lambda text: print(text, end="", flush=True),
    )
    pr = await h.pipeline(
        [
            FunctionTask(fn=make_generate_script(topic, output_dir)),           # 0
            make_script_review_dialogue(topic),                                  # 1
            FunctionTask(fn=make_extract_approved_script(topic, output_dir)),   # 2
            Parallel(tasks=[                                                     # 3
                FunctionTask(fn=make_generate_images(topic, output_dir)),       # 3.0 → results[3]
                FunctionTask(fn=make_generate_tts(topic, output_dir)),          # 3.1 → results[4]
            ]),
            FunctionTask(fn=make_merge_with_subs(topic, output_dir)),           # 4
        ],
        name=f"shortvideo-{topic[:20]}",
    )

    video_path: str = pr.results[-1].output
    print(f"\n{'='*50}")
    print(f"✅ Pipeline 完成 | 耗时 {pr.total_duration_seconds:.1f}s")
    print(f"   视频: {video_path}")
    print(f"{'='*50}")
    return video_path


def main():
    validate_api_key()
    parser = argparse.ArgumentParser(description="短视频自动生成（Harness 流水线）")
    parser.add_argument("topic", help="视频话题，如 'DeepSeek最新发布'")
    parser.add_argument("--output", default="./output", help="输出目录（默认 ./output）")
    args = parser.parse_args()
    asyncio.run(run(args.topic, Path(args.output).resolve()))


if __name__ == "__main__":
    main()
