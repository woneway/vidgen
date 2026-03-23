"""minimax.py — 兼容性模块，委托给 modules/providers

旧版 pipeline.py / pipeline_harness.py 直接 import minimax，
统一委托到 modules/providers 保证只有一份实现。
"""
from modules.providers import chat, generate_image, download_file  # noqa: F401

__all__ = ["chat", "generate_image", "download_file"]
