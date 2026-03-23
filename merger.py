"""ffmpeg - 图片轮播 + TTS 合成短视频"""
import asyncio
from pathlib import Path


async def images_to_video(
    image_paths: list[str],
    tts_path: str,
    output_path: str,
    music_path: str | None = None,
    music_volume: float = 0.12,
) -> str:
    """
    图片轮播 + TTS 配音 → MP4

    每张图片展示时长 = 总音频时长 / 图片数量
    带淡入淡出转场
    """
    n = len(image_paths)

    # 先获取音频时长
    probe = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", tts_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await probe.communicate()
    import json
    duration = float(json.loads(out)["format"]["duration"])
    per_image = duration / n

    # 构建 filter_complex：每张图缩放 + Ken Burns 效果 + 转场
    inputs = []
    for p in image_paths:
        inputs += ["-loop", "1", "-t", str(per_image + 0.5), "-i", p]

    filter_parts = []
    for i in range(n):
        # 缩放到 1080x1920（抖音竖屏），轻微 zoom-in 效果
        filter_parts.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"zoompan=z='min(zoom+0.0008,1.05)':d={int(per_image * 25)}:s=1080x1920:fps=25[v{i}]"
        )

    # 拼接所有图片片段
    concat_in = "".join(f"[v{i}]" for i in range(n))
    filter_parts.append(f"{concat_in}concat=n={n}:v=1:a=0[vout]")
    filter_complex = ";".join(filter_parts)

    # 基础命令：图片 + filter + TTS
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-i", tts_path,
    ]

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
        raise RuntimeError(f"ffmpeg 失败:\n{stderr.decode()[-1000:]}")

    return output_path
