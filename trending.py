"""热点抓取 - 微博/百度热搜"""
import httpx


async def fetch_weibo_hot() -> list[str]:
    """抓取微博热搜榜，返回 top10 话题"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://weibo.com/ajax/side/hotSearch",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            r.raise_for_status()
            data = r.json()
            topics = [
                item["word"]
                for item in data["data"]["realtime"]
                if item.get("word")
            ]
            return topics[:10]
    except Exception as e:
        print(f"微博热搜抓取失败: {e}")
        return []


async def fetch_baidu_hot() -> list[str]:
    """抓取百度热搜榜"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://top.baidu.com/board?tab=realtime",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            r.raise_for_status()
            import re
            topics = re.findall(r'"query":"([^"]+)"', r.text)
            topics = list(dict.fromkeys(topics))[:10]  # 去重保序
            if not topics:
                print("百度热搜解析结果为空，页面结构可能已变更")
            return topics
    except Exception as e:
        print(f"百度热搜抓取失败: {e}")
        return []


async def get_hot_topics() -> list[str]:
    """合并多源热点，返回去重后的话题列表"""
    import asyncio
    weibo, baidu = await asyncio.gather(fetch_weibo_hot(), fetch_baidu_hot())
    seen = set()
    merged = []
    for topic in weibo + baidu:
        if topic not in seen:
            seen.add(topic)
            merged.append(topic)
    return merged[:15]
