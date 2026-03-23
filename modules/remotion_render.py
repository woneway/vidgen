"""Remotion 渲染桥接 — 写 props.json 并调用 Remotion CLI 渲染视频

Remotion 通过内置 dev server 提供静态资源（public/ 目录），
因此需要将音频和图片文件复制到 remotion/public/assets/ 下，
并在 props 中使用 staticFile() 兼容的相对路径。
"""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

from modules.code_analyzer import ProjectAnalysis

# Remotion 子项目相对于本文件的路径
_REMOTION_DIR = Path(__file__).resolve().parent.parent / "remotion"
_ASSETS_DIR = _REMOTION_DIR / "public" / "assets"


def _is_remotion_available() -> bool:
    """检查 Remotion 子项目和 Node.js 环境是否可用"""
    if not (_REMOTION_DIR / "package.json").exists():
        return False
    if not (_REMOTION_DIR / "node_modules").exists():
        return False
    return shutil.which("npx") is not None


async def ensure_remotion_installed() -> bool:
    """检查并安装 Remotion 依赖，返回是否可用"""
    if not (_REMOTION_DIR / "package.json").exists():
        print("  [Remotion] 未找到 remotion/ 子项目")
        return False

    if shutil.which("npx") is None:
        print("  [Remotion] 未找到 npx，请安装 Node.js")
        return False

    if not (_REMOTION_DIR / "node_modules").exists():
        print("  [Remotion] 首次使用，安装依赖...")
        proc = await asyncio.create_subprocess_exec(
            "npm", "install",
            cwd=str(_REMOTION_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            print(f"  [Remotion] npm install 失败: {stderr.decode()[-500:]}")
            return False
        print("  [Remotion] 依赖安装完成")

    return True


def _stage_asset(src_path: str, safe_name: str, filename: str) -> str:
    """复制资源文件到 remotion/public/assets/{safe}/ 目录，
    返回 staticFile() 可用的相对路径（如 'assets/vidgen/tts.mp3'）
    """
    dest_dir = _ASSETS_DIR / safe_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    shutil.copy2(src_path, dest)
    # 返回相对于 public/ 的路径
    return f"assets/{safe_name}/{filename}"


def _build_props(
    script: dict,
    analysis: ProjectAnalysis,
    image_paths: dict[int, str],
    tts_path: str,
    audio_duration: float,
    safe_name: str,
) -> dict:
    """将 Python 数据结构转为 Remotion 所需的 camelCase props

    音频和图片路径会被复制到 remotion/public/assets/ 下，
    props 中存储 staticFile() 兼容的相对路径。
    """
    # 复制 TTS 音频到 public/assets/
    audio_rel = _stage_asset(tts_path, safe_name, Path(tts_path).name)

    scenes = []
    for i, s in enumerate(script["scenes"]):
        scene = {
            "narration": s["narration"],
            "imagePrompt": s.get("image_prompt", ""),
            "visualType": s.get("visual_type", "ai_image"),
        }
        if i in image_paths:
            # 复制图片到 public/assets/
            img_src = image_paths[i]
            img_name = Path(img_src).name
            scene["imagePath"] = _stage_asset(img_src, safe_name, img_name)
        scenes.append(scene)

    code_examples = [
        {
            "filename": ex["filename"],
            "code": ex["code"],
            "language": ex["language"],
        }
        for ex in (analysis.code_examples or [])
    ]

    github_stats = None
    if analysis.github_stats:
        github_stats = {
            "stars": analysis.github_stats.get("stars", 0),
            "forks": analysis.github_stats.get("forks", 0),
        }

    return {
        "title": script.get("title", analysis.name),
        "tags": script.get("tags", []),
        "scenes": scenes,
        "analysis": {
            "name": analysis.name,
            "description": analysis.description,
            "techStack": analysis.tech_stack,
            "totalLoc": analysis.total_loc,
            "totalFiles": analysis.total_files,
            "dependencyCount": len(analysis.dependencies),
            "testInfo": analysis.test_info,
            "githubUrl": analysis.github_url,
            "githubStats": github_stats,
            "structure": analysis.structure,
            "codeExamples": code_examples,
        },
        "audioPath": audio_rel,
        "audioDuration": audio_duration,
    }


def _cleanup_assets(safe_name: str) -> None:
    """渲染完成后清理复制的临时资源"""
    dest_dir = _ASSETS_DIR / safe_name
    if dest_dir.exists():
        shutil.rmtree(dest_dir)


async def render_with_remotion(
    script: dict,
    analysis: ProjectAnalysis,
    image_paths: dict[int, str],
    tts_path: str,
    audio_duration: float,
    output_path: str,
) -> str:
    """写 props.json 并调用 Remotion CLI 渲染视频

    Returns:
        输出视频的路径

    Raises:
        RuntimeError: 渲染失败时
    """
    safe_name = Path(output_path).stem.replace("_final", "")

    # 1. 构建 props（会复制资源到 public/assets/）
    props = _build_props(
        script, analysis, image_paths, tts_path, audio_duration, safe_name,
    )

    # 2. 写 props.json（放在 output 同目录下）
    output_dir = Path(output_path).parent
    props_path = output_dir / "remotion_props.json"
    props_path.write_text(
        json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(f"  [Remotion] Props 写入: {props_path}")

    # 3. 计算帧数
    fps = 25
    duration_frames = max(1, round(audio_duration * fps))

    # 4. 调用 Remotion CLI
    abs_output = str(Path(output_path).resolve())
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "CodeIntro", abs_output,
        f"--props={props_path.resolve()}",
        "--width=1080",
        "--height=1920",
        f"--fps={fps}",
    ]

    print(f"  [Remotion] 开始渲染 ({duration_frames} 帧)...")
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(_REMOTION_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode()[-1500:] if stderr else "unknown error"
            raise RuntimeError(
                f"Remotion 渲染失败 (code={proc.returncode}):\n{error_msg}"
            )

        print(f"  [Remotion] 渲染完成: {output_path}")
        return output_path
    finally:
        # 清理临时资源
        _cleanup_assets(safe_name)
