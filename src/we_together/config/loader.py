"""配置加载器：优先 we_together.toml，缺失字段回退到 env。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # Python 3.11+
    import tomllib  # type: ignore
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


@dataclass
class WeTogetherConfig:
    llm_provider: str = "mock"
    daily_budget_self: int = 3
    daily_budget_pair: int = 2
    cache_ttl_seconds: int = 3600
    retrieval_max_memories: int = 20
    retrieval_max_relations: int = 10
    retrieval_max_states: int = 30
    db_root: str = "."
    tenant_id: str = "default"
    extras: dict = field(default_factory=dict)


def load_config(config_path: Path | None = None) -> WeTogetherConfig:
    cfg = WeTogetherConfig()

    if config_path and config_path.exists():
        data = tomllib.loads(config_path.read_text())
        _merge_dict_into_cfg(cfg, data)

    # env 覆盖
    if v := os.environ.get("WE_TOGETHER_LLM_PROVIDER"):
        cfg.llm_provider = v
    if v := os.environ.get("WE_TOGETHER_DB_ROOT"):
        cfg.db_root = v
    if v := os.environ.get("WE_TOGETHER_TENANT_ID"):
        cfg.tenant_id = v
    if v := os.environ.get("WE_TOGETHER_CACHE_TTL"):
        try:
            cfg.cache_ttl_seconds = int(v)
        except ValueError:
            pass

    return cfg


def _merge_dict_into_cfg(cfg: WeTogetherConfig, data: dict) -> None:
    for section in ("llm", "runtime", "storage"):
        sect = data.get(section) or {}
        for k, v in sect.items():
            field_name = f"{section}_{k}" if not hasattr(cfg, k) else k
            if hasattr(cfg, field_name):
                setattr(cfg, field_name, v)
            elif hasattr(cfg, k):
                setattr(cfg, k, v)
            else:
                cfg.extras[f"{section}.{k}"] = v
