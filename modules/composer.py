"""视频合成模块 — ffmpeg 图片轮播 + 音频 → MP4"""
from __future__ import annotations

import asyncio
import json

from modules.constants import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS


async def get_audio_duration(audio_path: str) -> float:
    """通过 ffprobe 获取音频时长（秒）"""
    probe = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", audio_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await probe.communicate()
    if probe.returncode != 0:
        raise RuntimeError(f"ffprobe 失败 (returncode={probe.returncode}): {err.decode()}")
    return float(json.loads(out)["format"]["duration"])


async def images_to_video(
    image_paths: list[str],
    tts_path: str,
    output_path: str,
    music_path: str | None = None,
    music_volume: float = 0.12,
) -> str:
    """
    图片轮播 + TTS 配音 → MP4

    - 每张图片时长 = 总音频时长 / 图片数量
    - Ken Burns 轻微 zoom-in 效果
    - 可选背景音乐混合
    """
    n = len(image_paths)
    duration = await get_audio_duration(tts_path)
    per_image = duration / n

    inputs = []
    for p in image_paths:
        inputs += ["-loop", "1", "-t", str(per_image), "-i", p]

    filter_parts = []
    for i in range(n):
        filter_parts.append(
            f"[{i}:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
            f"zoompan=z='min(zoom+0.0008,1.05)':d={int(per_image * VIDEO_FPS)}"
            f":s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={VIDEO_FPS}[v{i}]"
        )

    concat_in = "".join(f"[v{i}]" for i in range(n))
    filter_parts.append(f"{concat_in}concat=n={n}:v=1:a=0[vout]")
    filter_complex = ";".join(filter_parts)

    cmd = ["ffmpeg", "-y", *inputs, "-i", tts_path]

    if music_path:
        cmd += ["-i", music_path]
        audio_filter = (
            f"[{n + 1}:a]volume={music_volume}[bgm];"
            f"[{n}:a][bgm]amix=inputs=2:duration=first[aout]"
        )
        filter_complex += ";" + audio_filter
        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "[aout]",
        ]
    else:
        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", f"{n}:a",
        ]

    cmd += [
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-r", str(VIDEO_FPS),
        output_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败:\n{stderr.decode()[-1000:]}")

    return output_path
