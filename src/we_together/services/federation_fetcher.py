"""联邦拉取服务：按 policy 真从外部 skill 拉人物数据。

Backend Protocol（pluggable）:
  - LocalFileBackend: 读 <root>/federation/<skill_name>/<ext_person_id>.json
  - HTTPBackend: GET <base_url>/persons/<ext_person_id>（stub）

Fetcher：
  - 内存 cache + TTL（避免重复调 backend）
  - fetch_eager_refs(db_path) 读 external_person_refs policy='eager' 的引用
  - get_remote_person(ref) 按 backend 拉数据
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from we_together.services.federation_service import get_eager_refs, list_external_refs

DEFAULT_CACHE_TTL_SECONDS = 300


class FederationBackend(Protocol):
    name: str

    def fetch_remote_person(self, skill_name: str, external_person_id: str) -> dict | None: ...


class LocalFileBackend:
    name = "local_file"

    def __init__(self, root: Path):
        self.root = root

    def fetch_remote_person(self, skill_name: str, external_person_id: str) -> dict | None:
        path = self.root / "federation" / skill_name / f"{external_person_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


class HTTPBackend:
    """HTTP stub backend（延迟 import requests/httpx）。"""
    name = "http"

    def __init__(self, *, base_url: str, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def fetch_remote_person(self, skill_name: str, external_person_id: str) -> dict | None:  # pragma: no cover
        try:
            import urllib.request
        except ImportError as exc:
            raise RuntimeError("urllib unavailable") from exc
        url = f"{self.base_url}/skill/{skill_name}/persons/{external_person_id}"
        req = urllib.request.Request(url)
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status != 200:
                    return None
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None


@dataclass
class FederationFetcher:
    backend: FederationBackend
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS
    _cache: dict[tuple[str, str], tuple[float, dict]] = field(default_factory=dict)

    def get_remote_person(
        self, skill_name: str, external_person_id: str,
    ) -> dict | None:
        key = (skill_name, external_person_id)
        hit = self._cache.get(key)
        now = time.time()
        if hit and now - hit[0] < self.cache_ttl_seconds:
            return hit[1]
        data = self.backend.fetch_remote_person(skill_name, external_person_id)
        if data is not None:
            self._cache[key] = (now, data)
        return data

    def fetch_eager_refs(self, db_path: Path) -> list[dict]:
        """读 policy='eager' 的 external_person_refs，挨个 get_remote_person。"""
        refs = get_eager_refs(db_path)
        out: list[dict] = []
        for ref in refs:
            data = self.get_remote_person(
                ref["external_skill_name"], ref["external_person_id"],
            )
            out.append({
                "ref": ref,
                "remote_data": data,
                "fetched": data is not None,
            })
        return out

    def invalidate_cache(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        return count


def build_default_fetcher(root: Path) -> FederationFetcher:
    return FederationFetcher(backend=LocalFileBackend(root))


def inject_eager_into_participants(
    package: dict, fetched: list[dict],
) -> dict:
    """把 fetched 的远端 person 合并进 retrieval_package.participants。"""
    if not fetched:
        return package
    remote_participants = []
    for item in fetched:
        if not item["fetched"]:
            continue
        d = item["remote_data"] or {}
        ref = item["ref"]
        remote_participants.append({
            "person_id": f"remote::{ref['external_skill_name']}::{ref['external_person_id']}",
            "display_name": d.get("display_name") or ref.get("display_name"),
            "persona_summary": d.get("persona_summary"),
            "remote": True,
            "trust_level": ref.get("trust_level"),
            "source_skill": ref["external_skill_name"],
        })
    if remote_participants:
        package.setdefault("participants", []).extend(remote_participants)
        package.setdefault("federation", {})["remote_participants"] = len(remote_participants)
    return package
