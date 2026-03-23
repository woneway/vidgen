"""竞品调研模块 — 通过 LLM 分析项目定位并对比竞品"""
from __future__ import annotations

from dataclasses import dataclass, field

from modules import providers

_COMPETITOR_SYSTEM = """你是一位资深技术分析师，擅长开源项目调研和竞品分析。

根据给定的项目信息，完成以下任务：
1. 列出 3-5 个最相关的竞品/替代方案
2. 分析该项目相比竞品的差异化优势
3. 给出市场定位总结

严格输出 JSON，格式如下：
{
  "competitors": [
    {
      "name": "竞品名称",
      "description": "一句话描述",
      "url": "项目URL（如有）",
      "pros": ["优势1", "优势2"],
      "cons": ["劣势1", "劣势2"]
    }
  ],
  "differentiators": ["差异化优势1", "差异化优势2", "差异化优势3"],
  "market_position": "一段话描述该项目在市场中的定位和价值"
}"""


@dataclass
class CompetitorAnalysis:
    competitors: list[dict] = field(default_factory=list)
    differentiators: list[str] = field(default_factory=list)
    market_position: str = ""


async def research_competitors(
    project_name: str,
    description: str,
    tech_stack: list[str],
) -> CompetitorAnalysis:
    """通过 LLM 分析项目定位，生成竞品对比"""
    from modules.script import parse_script_json

    prompt = (
        f"项目名称: {project_name}\n"
        f"项目描述: {description}\n"
        f"技术栈: {', '.join(tech_stack)}\n\n"
        f"请分析该项目的竞品和市场定位。"
    )

    try:
        raw = await providers.chat(prompt, system=_COMPETITOR_SYSTEM)
        data = parse_script_json(raw)

        return CompetitorAnalysis(
            competitors=data.get("competitors", []),
            differentiators=data.get("differentiators", []),
            market_position=data.get("market_position", ""),
        )
    except Exception as e:
        print(f"  竞品调研失败({e})，使用空结果")
        return CompetitorAnalysis(
            market_position=f"{project_name} 是一个基于 {', '.join(tech_stack[:3])} 的项目。"
        )
