"""统一异常层级：WeTogetherError / IngestError / RetrievalError / PatchError / ConfigError。"""
from __future__ import annotations


class WeTogetherError(Exception):
    """顶层基类。所有 we_together 抛出的 domain 异常都继承它。"""


class IngestError(WeTogetherError):
    """importer / ingestion 层错误。"""


class RetrievalError(WeTogetherError):
    """runtime retrieval / skill runtime 层错误。"""


class PatchError(WeTogetherError):
    """patch 构造 / 应用层错误。"""


class ConfigError(WeTogetherError):
    """配置加载 / 校验错误。"""


class SchemaVersionError(WeTogetherError):
    """migration 版本冲突。"""
