"""federation_client（Phase 42 FD）：从远端 skill 的 HTTP endpoint 拉数据。

用法:
  from we_together.services.federation_client import FederationClient
  c = FederationClient("http://peer.example:7781")
  persons = c.list_persons()
  person = c.get_person("person_alice")
  memories = c.list_memories(owner_id="person_alice")

设计:
- 纯 stdlib urllib.request
- 不依赖 httpx / requests
- 超时默认 5s；失败抛 RuntimeError 含 status + body
- 客户端不做身份映射；交由 federation_fetcher 处理跨图谱 register
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass
class FederationClient:
    base_url: str
    timeout: float = 5.0
    bearer_token: str | None = None

    def _urlopen(self, req: urllib.request.Request):
        host = urllib.parse.urlparse(req.full_url).hostname or ""
        if host in {"127.0.0.1", "localhost"}:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            return opener.open(req, timeout=self.timeout)
        return urllib.request.urlopen(req, timeout=self.timeout)

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = self.base_url.rstrip("/") + path
        if params:
            url += "?" + urllib.parse.urlencode({
                k: v for k, v in params.items() if v is not None
            })
        headers = {
            "Accept": "application/json",
            "User-Agent": "we-together-federation-client/1",
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with self._urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"federation GET {path} failed: {e.code} {e.reason}"
            ) from e

    def capabilities(self) -> dict:
        return self._get("/federation/v1/capabilities")

    def _post(self, path: str, payload: dict) -> dict:
        url = self.base_url.rstrip("/") + path
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "we-together-federation-client/1",
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with self._urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                body_text = e.read().decode("utf-8")
            except Exception:
                body_text = ""
            detail = f" body={body_text[:200]}" if body_text else ""
            raise RuntimeError(
                f"federation POST {path} failed: {e.code} {e.reason}{detail}"
            ) from e

    def list_persons(self, *, limit: int = 50) -> dict:
        return self._get("/federation/v1/persons", {"limit": limit})

    def get_person(self, person_id: str) -> dict | None:
        try:
            return self._get(f"/federation/v1/persons/{person_id}")
        except RuntimeError as e:
            if "404" in str(e):
                return None
            raise

    def list_memories(
        self, *, owner_id: str | None = None, limit: int = 50,
    ) -> dict:
        return self._get(
            "/federation/v1/memories",
            {"owner_id": owner_id, "limit": limit},
        )

    def create_memory(
        self,
        *,
        summary: str,
        owner_person_ids: list[str],
        source_skill_name: str | None = None,
        source_locator: str | None = None,
        scene_id: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        return self._post(
            "/federation/v1/memories",
            {
                "summary": summary,
                "owner_person_ids": owner_person_ids,
                "source_skill_name": source_skill_name,
                "source_locator": source_locator,
                "scene_id": scene_id,
                "metadata": metadata or {},
            },
        )
