"""Pipeline 基类 — 所有场景 Pipeline 的统一契约"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineResult:
    """任意 Pipeline 的标准化输出"""
    topic: str
    title: str
    output_path: str
    tags: list[str] = field(default_factory=list)
    # 各场景可扩展的元数据（股票 ticker、产品 URL 等）
    metadata: dict = field(default_factory=dict)


class BasePipeline(ABC):
    """
    短视频生成 Pipeline 抽象基类。

    每个场景（热点、股票、产品）实现自己的 run()，
    共享输出目录管理和文件名工具方法。
    """

    #: Pipeline 标识符，用于日志和文件名
    name: str = "base"

    def __init__(self, output_dir: str | Path = "./output"):
        self.output_dir = Path(output_dir)

    def _ensure_output_dir(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir

    @staticmethod
    def _safe_name(topic: str) -> str:
        """生成文件名安全的话题前缀"""
        return topic[:20].replace(" ", "_").replace("/", "_")

    @abstractmethod
    async def run(self, topic: str) -> PipelineResult:
        """执行完整的视频生成流程"""
        ...
