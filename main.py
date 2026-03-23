"""入口 — 按场景路由到对应 Pipeline"""
from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv
load_dotenv()

import trending
from modules.providers import validate_api_key
from pipelines.hot_topic import HotTopicPipeline


async def _run(topic: str, output_dir: str = "./output"):
    pipeline = HotTopicPipeline(output_dir=output_dir)
    result = await pipeline.run(topic)
    print(f"\n话题: {result.topic}")
    print(f"视频: {result.output_path}")


async def _run_code_intro(
    project_path: str,
    output_dir: str = "./output",
    num_scenes: int = 7,
    music_path: str | None = None,
):
    from pipelines.code_intro import CodeIntroPipeline
    pipeline = CodeIntroPipeline(
        output_dir=output_dir,
        num_scenes=num_scenes,
        music_path=music_path,
    )
    result = await pipeline.run(project_path)
    print(f"\n项目: {result.topic}")
    print(f"视频: {result.output_path}")


async def _run_trending(output_dir: str = "./output"):
    print("抓取热点中...")
    topics = await trending.get_hot_topics()
    if not topics:
        print("热点抓取失败，使用默认话题")
        topics = ["AI技术最新进展"]

    print(f"\n获取到 {len(topics)} 个热点：")
    for i, t in enumerate(topics[:5], 1):
        print(f"  {i}. {t}")

    await _run(topics[0], output_dir)


def _extract_flag(args: list[str], flag: str) -> tuple[str | None, list[str]]:
    """提取 --flag value 参数，返回 (value, remaining_args)"""
    if flag not in args:
        return None, args
    idx = args.index(flag)
    if idx + 1 >= len(args):
        print(f"错误：{flag} 后需要指定值")
        sys.exit(1)
    value = args[idx + 1]
    remaining = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]
    return value, remaining


if __name__ == "__main__":
    validate_api_key()
    args = sys.argv[1:]

    # 提取通用参数
    output_dir, args = _extract_flag(args, "--output")
    output_dir = output_dir or "./output"

    pipeline_type, args = _extract_flag(args, "--pipeline")

    scenes_str, args = _extract_flag(args, "--scenes")
    num_scenes = int(scenes_str) if scenes_str else 7

    music_path, args = _extract_flag(args, "--music")

    if pipeline_type == "code_intro":
        if not args:
            print("错误：code_intro pipeline 需要指定项目路径")
            print("用法：python main.py --pipeline code_intro /path/to/project")
            sys.exit(1)
        project_path = args[0]
        asyncio.run(_run_code_intro(project_path, output_dir, num_scenes, music_path))
    elif args:
        asyncio.run(_run(" ".join(args), output_dir))
    else:
        asyncio.run(_run_trending(output_dir))
