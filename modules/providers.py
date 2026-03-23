"""MiniMax API client — 封装所有外部 API 调用"""
import os
import httpx

BASE_URL = os.getenv("MINIMAX_API_HOST", "https://api.minimaxi.com")
API_KEY = os.getenv("MINIMAX_API_KEY", "")


def validate_api_key() -> None:
    """校验 API Key 已配置，否则提前报错，避免深入执行后才失败"""
    if not API_KEY:
        raise EnvironmentError(
            "缺少 MINIMAX_API_KEY 环境变量。\n"
            "请在 .env 文件或环境中设置：export MINIMAX_API_KEY=your_key"
        )


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


async def chat(prompt: str, system: str = "") -> str:
    """MiniMax 文本生成"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{BASE_URL}/v1/text/chatcompletion_v2",
            headers=_headers(),
            json={"model": "MiniMax-Text-01", "messages": messages, "max_tokens": 2000},
        )
        r.raise_for_status()
        data = r.json()
        if data.get("base_resp", {}).get("status_code") != 0:
            raise RuntimeError(f"Chat 错误: {data['base_resp']}")
        return data["choices"][0]["message"]["content"]


async def generate_image(prompt: str, aspect_ratio: str = "9:16") -> bytes:
    """MiniMax 文生图，返回图片 bytes"""
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"{BASE_URL}/v1/image_generation",
            headers=_headers(),
            json={
                "model": "image-01",
                "prompt": prompt,
                "n": 1,
                "aspect_ratio": aspect_ratio,
            },
        )
        r.raise_for_status()
        data = r.json()
        if data.get("base_resp", {}).get("status_code") != 0:
            raise RuntimeError(f"图片生成错误: {data['base_resp']}")

        image_url = data["data"]["image_urls"][0]
        r2 = await client.get(image_url)
        r2.raise_for_status()
        return r2.content


async def download_file(file_id: str) -> bytes:
    """通过 file_id 下载文件内容"""
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            f"{BASE_URL}/v1/files/retrieve",
            headers=_headers(),
            params={"file_id": file_id},
        )
        r.raise_for_status()
        download_url = r.json()["file"]["download_url"]

        r2 = await client.get(download_url)
        r2.raise_for_status()
        return r2.content
