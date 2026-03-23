"""脚本生成模块 — LLM 生成分镜脚本，解析并持久化"""
from __future__ import annotations

import json
import re
from pathlib import Path

from modules import providers

# 图片 prompt 质量增强后缀
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


def safe_name(topic: str) -> str:
    """生成文件名安全的话题前缀"""
    return topic[:20].replace(" ", "_").replace("/", "_")


def parse_script_json(raw: str) -> dict:
    """
    从 LLM 响应中健壮地提取 JSON。
    支持：纯 JSON、markdown 代码块包裹、前后有散文
    """
    # 1. 尝试剥离 markdown 代码块
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if fence_match:
        return json.loads(fence_match.group(1))

    # 2. 提取最外层 {} 块
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"LLM 响应中未找到 JSON 对象:\n{raw[:500]}")

    try:
        return json.loads(raw[start:end])
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"JSON 解析失败: {exc}\n原始响应(前500字):\n{raw[:500]}"
        ) from exc


def validate_script(script: dict) -> None:
    """校验 LLM 返回的脚本结构，提前暴露缺字段问题"""
    if "scenes" not in script:
        raise ValueError("脚本缺少 'scenes' 字段")
    scenes = script["scenes"]
    if not isinstance(scenes, list) or len(scenes) == 0:
        raise ValueError(f"'scenes' 必须是非空列表，实际: {scenes!r}")
    for i, scene in enumerate(scenes):
        if "image_prompt" not in scene or "narration" not in scene:
            raise ValueError(f"scenes[{i}] 缺少 'image_prompt' 或 'narration'")
    if "title" not in script:
        raise ValueError("脚本缺少 'title' 字段")


async def generate_script(topic: str, output_dir: Path) -> dict:
    """生成分镜脚本，校验结构，持久化 JSON 文件，返回 script dict"""
    raw = await providers.chat(f"话题：{topic}", system=SCRIPT_SYSTEM)
    script = parse_script_json(raw)
    validate_script(script)

    script_path = output_dir / f"{safe_name(topic)}_script.json"
    script_path.write_text(
        json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return script
