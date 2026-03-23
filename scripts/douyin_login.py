"""抖音首次登录 — 生成并保存 cookie

运行方式：
    python scripts/douyin_login.py

会打开 Chrome 浏览器，扫码或手机号登录抖音创作者中心后，
点击 Playwright 调试器右上角的「继续」按钮，cookie 自动保存。

之后运行 `python main.py --publish` 即可自动发布，无需重复登录。
"""
import asyncio
import sys
from pathlib import Path

# 项目根目录加入路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from modules.douyin_publisher import ensure_login, _cookie_path


async def main():
    path = _cookie_path()
    print(f"Cookie 将保存到: {path}")
    print("即将打开浏览器，请扫码登录抖音创作者中心...")
    print("登录成功后点击调试器的「继续」按钮\n")
    ok = await ensure_login(handle=True)
    if ok:
        print(f"\n✅ 登录成功！Cookie 已保存到 {path}")
    else:
        print("\n❌ 登录失败，请重试")


asyncio.run(main())
