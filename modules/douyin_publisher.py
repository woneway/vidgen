"""抖音自动发布模块 — 基于 social-auto-upload (Playwright 浏览器自动化)

首次使用需要登录：
    python scripts/douyin_login.py

之后 cookie 自动复用，无需重复登录。

配置（.env）：
    DOUYIN_COOKIE_FILE  — cookie 文件路径（默认 ~/.vidgen/douyin_cookie.json）
    CHROME_PATH         — Chrome 可执行文件路径（留空使用 Playwright 内置 Chromium）
    CHROME_HEADLESS     — 是否无头模式，true/false（默认 false）
"""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path

# ── 注入 SAU 的 conf 模块（避免修改 submodule 内文件）──────────────────────
_SAU_PATH = Path(__file__).parent.parent / "vendor" / "social-auto-upload"
if str(_SAU_PATH) not in sys.path:
    sys.path.insert(0, str(_SAU_PATH))

if "conf" not in sys.modules:
    _conf = types.ModuleType("conf")
    _conf.LOCAL_CHROME_PATH = os.environ.get("CHROME_PATH", "")
    _conf.LOCAL_CHROME_HEADLESS = os.environ.get("CHROME_HEADLESS", "false").lower() == "true"
    _conf.BASE_DIR = _SAU_PATH
    sys.modules["conf"] = _conf

# ── 导入 SAU ────────────────────────────────────────────────────────────────
from playwright.async_api import async_playwright  # noqa: E402
from uploader.douyin_uploader.main import DouYinVideo  # noqa: E402
from utils.base_social_media import set_init_script  # noqa: E402

_DEFAULT_COOKIE_FILE = Path.home() / ".vidgen" / "douyin_cookie.json"


def _cookie_path() -> Path:
    env = os.environ.get("DOUYIN_COOKIE_FILE", "")
    return Path(env) if env else _DEFAULT_COOKIE_FILE


def _chrome_opts() -> dict:
    """返回 chromium.launch 参数，优先用系统 Chrome，支持代理"""
    headless = os.environ.get("CHROME_HEADLESS", "false").lower() == "true"
    path = os.environ.get("CHROME_PATH", "")
    proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy", "")
    opts: dict = {"headless": headless}
    if path:
        opts["executable_path"] = path
    if proxy:
        opts["proxy"] = {"server": proxy}
    return opts


async def _cookie_auth(account_file: str) -> bool:
    """检查 cookie 是否有效（覆盖 SAU 版本以支持系统 Chrome）"""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(**_chrome_opts())
        ctx = await browser.new_context(storage_state=account_file)
        ctx = await set_init_script(ctx)
        page = await ctx.new_page()
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        try:
            await page.wait_for_url(
                "https://creator.douyin.com/creator-micro/content/upload", timeout=5000
            )
        except Exception:
            await ctx.close()
            await browser.close()
            return False
        if await page.get_by_text("手机号登录").count() or await page.get_by_text("扫码登录").count():
            await ctx.close()
            await browser.close()
            return False
        await ctx.close()
        await browser.close()
        return True


_USER_DATA_DIR = Path.home() / ".vidgen" / "chrome_profile"


async def _gen_cookie(account_file: str) -> None:
    """打开浏览器让用户手动登录并保存 cookie。
    使用持久化用户目录，绕过抖音/Google 的自动化检测。
    """
    _USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    opts = _chrome_opts()
    headless = opts.pop("headless", False)
    chrome_path = opts.get("executable_path", "")

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(_USER_DATA_DIR),
            headless=headless,
            executable_path=chrome_path or None,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )
        ctx = await set_init_script(ctx)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://creator.douyin.com/")
        await page.pause()  # 用户登录后点「继续」
        await ctx.storage_state(path=account_file)
        await ctx.close()


async def ensure_login(handle: bool = True) -> bool:
    """验证 cookie 是否有效；handle=True 时失效会自动打开浏览器让用户登录"""
    path = _cookie_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    account_file = str(path)

    if path.exists() and await _cookie_auth(account_file):
        return True
    if not handle:
        return False

    from loguru import logger
    logger.info("[+] cookie 不存在或已失效，打开浏览器，请扫码登录后点「继续」")
    await _gen_cookie(account_file)
    return True


async def publish(
    video_path: str,
    title: str,
    tags: list[str] | None = None,
    description: str = "",
    schedule: object = 0,
) -> None:
    """上传并发布视频到抖音。

    Args:
        video_path: MP4 文件路径
        title:      视频标题（≤30 字，超出自动截断）
        tags:       话题标签列表，不含 # 号（例如 ["AI", "A股"]）
        description: 暂不使用（抖音标题即文案入口），保留给未来扩展
        schedule:   0 = 立即发布；datetime 对象 = 定时发布
    """
    cookie_file = str(_cookie_path())

    # 验证登录状态（不自动弹窗，由调用方决定）
    path = _cookie_path()
    ok = path.exists() and await _cookie_auth(cookie_file)
    if not ok:
        raise RuntimeError(
            "抖音 cookie 无效或不存在，请先运行：python scripts/douyin_login.py"
        )

    # 清理标签：去掉 # 前缀，过滤空值
    clean_tags = [t.lstrip("#").strip() for t in (tags or []) if t.strip()]

    # 标题截断
    safe_title = title[:30]

    uploader = DouYinVideo(
        title=safe_title,
        file_path=video_path,
        tags=clean_tags,
        publish_date=schedule,
        account_file=cookie_file,
    )
    await uploader.main()
