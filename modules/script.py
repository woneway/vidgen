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


# ── Code Intro 脚本生成 ──────────────────────────────────────────────

_CODE_INTRO_SYSTEM = """你是技术短视频脚本创作专家，擅长将代码项目包装成引人入胜的介绍视频。

根据给定的项目分析数据和竞品对比，生成一个 30~60 秒的项目介绍视频脚本。

每个场景必须指定 visual_type，可选值：
- title_card: 标题卡（第一个场景必须用）
- ai_image: AI 生成的概念图
- code_snippet: 代码展示卡片
- data_card: 数据可视化卡片
- architecture: 架构/目录结构图
- ending_card: 结尾卡（最后一个场景必须用）

严格输出 JSON，格式如下：
{
  "title": "项目名 — 一句话 slogan",
  "scenes": [
    {
      "image_prompt": "English prompt for AI image generation (ignored for non-ai_image types)",
      "narration": "中文旁白文案（口语化，每段 20-40 字）",
      "visual_type": "title_card"
    }
  ],
  "tags": ["#tag1", "#tag2", "#tag3"]
}

叙事节奏建议：
1. title_card: 开场 — 项目名和定位
2. ai_image: 痛点场景 — 没有这个工具时的困境
3. ai_image/code_snippet: 核心功能展示
4. code_snippet: 关键用法示例
5. data_card: 数据亮点展示
6. ai_image: 竞品对比或差异化优势
7. ending_card: 总结 + CTA

注意：
- 旁白要口语化，适合配音朗读
- image_prompt 只对 ai_image 类型有效，用英文描述
- 整体旁白 150~250 字
- 场景数量按用户要求调整"""


def _validate_code_intro_script(script: dict) -> None:
    """校验 code intro 脚本结构"""
    validate_script(script)
    valid_types = {"title_card", "ai_image", "code_snippet", "data_card", "architecture", "ending_card"}
    for i, scene in enumerate(script["scenes"]):
        vtype = scene.get("visual_type", "ai_image")
        if vtype not in valid_types:
            raise ValueError(
                f"scenes[{i}] visual_type '{vtype}' 无效，"
                f"有效值: {valid_types}"
            )


async def generate_code_intro_script(
    analysis,
    competitors,
    output_dir: Path,
    num_scenes: int = 7,
) -> dict:
    """基于代码分析和竞品对比，生成项目介绍分镜脚本"""
    # 构建丰富的上下文
    tech_str = ", ".join(analysis.tech_stack[:8])
    features_str = "\n".join(f"- {f}" for f in analysis.key_features[:6])
    deps_str = ", ".join(analysis.dependencies[:10])

    competitor_info = ""
    if competitors.competitors:
        comp_lines = []
        for c in competitors.competitors[:3]:
            comp_lines.append(f"- {c['name']}: {c.get('description', '')}")
        competitor_info = "\n".join(comp_lines)

    diff_str = "\n".join(f"- {d}" for d in competitors.differentiators[:4])

    code_example_info = ""
    if analysis.code_examples:
        ex = analysis.code_examples[0]
        code_example_info = f"关键代码 ({ex['filename']}):\n```{ex['language']}\n{ex['code']}\n```"

    prompt = f"""项目名称: {analysis.name}
项目描述: {analysis.description}
技术栈: {tech_str}
代码规模: {analysis.total_loc} 行代码, {analysis.total_files} 个文件
依赖: {deps_str}
测试: {analysis.test_info}
GitHub: {analysis.github_url or '无'}
{'GitHub Stars: ' + str(analysis.github_stats.get('stars', 0)) if analysis.github_stats else ''}

核心功能:
{features_str}

{code_example_info}

竞品分析:
{competitor_info}

差异化优势:
{diff_str}

市场定位: {competitors.market_position}

请生成 {num_scenes} 个场景的项目介绍视频脚本。
第一个场景必须是 title_card，最后一个必须是 ending_card。"""

    raw = await providers.chat(prompt, system=_CODE_INTRO_SYSTEM)
    script = parse_script_json(raw)
    _validate_code_intro_script(script)

    script_path = output_dir / f"{safe_name(analysis.name)}_script.json"
    script_path.write_text(
        json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return script
