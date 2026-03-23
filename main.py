"""入口 — 按场景路由到对应 Pipeline"""
import asyncio
import sys

import trending
from modules.providers import validate_api_key
from pipelines.hot_topic import HotTopicPipeline


async def _run(topic: str, output_dir: str = "./output"):
    pipeline = HotTopicPipeline(output_dir=output_dir)
    result = await pipeline.run(topic)
    print(f"\n话题: {result.topic}")
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


if __name__ == "__main__":
    validate_api_key()
    args = sys.argv[1:]
    output_dir = "./output"

    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 >= len(args):
            print("错误：--output 后需要指定目录路径")
            sys.exit(1)
        output_dir = args[idx + 1]
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]

    if args:
        asyncio.run(_run(" ".join(args), output_dir))
    else:
        asyncio.run(_run_trending(output_dir))
