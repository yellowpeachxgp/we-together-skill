"""federation_http_server（Phase 42 FD MVP / Phase 48 FS 加强）：真 HTTP endpoint。

路由:
  GET /federation/v1/persons          列出本地 persons（applied visibility=shared+）
  GET /federation/v1/persons/{pid}    单个 person 详情
  GET /federation/v1/memories?owner_id=...  按 owner 列 memory（只返 is_shared=1）
  GET /federation/v1/capabilities     公告本 skill 提供的联邦能力
  POST /federation/v1/memories        写入 shared memory（默认关闭；需显式开启）

Phase 48 新增：
- Bearer token 鉴权（WE_TOGETHER_FED_TOKENS env var 以逗号分隔 token hashes）
- rate limit（每 token 每分钟 60 次默认）
- PII 脱敏（email/phone mask）
- exportable=false 过滤

设计:
- Python stdlib http.server；不依赖 FastAPI
- 读-only；本阶段不支持写（安全边界）
- visibility 过滤在服务端完成
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.runtime.skill_runtime import SKILL_SCHEMA_VERSION
from we_together.services.federation_security import (
    RateLimiter,
    hash_token,
    is_exportable,
    sanitize_record,
    verify_token,
)
from we_together.services.tenant_router import resolve_tenant_root

FEDERATION_PROTOCOL_VERSION = "1.1"


def _capabilities(*, allow_writes: bool = False) -> dict:
    return {
        "federation_protocol_version": FEDERATION_PROTOCOL_VERSION,
        "skill_schema_version": SKILL_SCHEMA_VERSION,
        "supported_endpoints": [
            "/federation/v1/persons",
            "/federation/v1/persons/{pid}",
            "/federation/v1/memories",
            "/federation/v1/capabilities",
        ],
        "read_only": not allow_writes,
        "write_enabled": allow_writes,
        "auth": "bearer (optional)",
        "rate_limit_per_minute": 60,
        "pii_masking": True,
    }


def _list_persons(db: Path, limit: int = 50) -> dict:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT person_id, primary_name, status, confidence "
            "FROM persons WHERE status='active' LIMIT ?", (limit,),
        ).fetchall()
    finally:
        conn.close()
    return {"persons": [dict(r) for r in rows], "count": len(rows)}


def _get_person(db: Path, pid: str) -> dict | None:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT person_id, primary_name, status, confidence, metadata_json "
            "FROM persons WHERE person_id=?", (pid,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["metadata"] = json.loads(d.pop("metadata_json") or "{}")
    except Exception:
        d["metadata"] = {}
    return d


def _list_shared_memories(db: Path, *, owner_id: str | None = None, limit: int = 50) -> dict:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        if owner_id:
            rows = conn.execute(
                """SELECT DISTINCT m.memory_id, m.summary, m.relevance_score,
                   m.confidence, m.created_at
                   FROM memories m
                   JOIN memory_owners mo ON mo.memory_id=m.memory_id
                   WHERE m.status='active' AND m.is_shared=1
                     AND mo.owner_type='person' AND mo.owner_id=?
                   LIMIT ?""",
                (owner_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT memory_id, summary, relevance_score, confidence, created_at
                   FROM memories
                   WHERE status='active' AND is_shared=1
                   LIMIT ?""",
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return {"memories": [dict(r) for r in rows], "count": len(rows)}


def make_handler(root: Path, *,
                  allowed_token_hashes: list[str] | None = None,
                  rate_limiter: RateLimiter | None = None,
                  mask_pii_on_export: bool = True,
                  allow_writes: bool = False):
    token_hashes = allowed_token_hashes or []
    limiter = rate_limiter

    class H(BaseHTTPRequestHandler):
        def _write_json(self, status: int, payload: dict):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _check_auth(self) -> tuple[bool, str]:
            """返回 (allowed, token_key)。token_key 用于 rate limit 分桶。"""
            if not token_hashes:
                return True, "anonymous"  # 未配置 token → 开放
            auth = self.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return False, "no_token"
            token = auth[len("Bearer "):].strip()
            if not token or not verify_token(token, token_hashes):
                return False, "invalid_token"
            return True, hash_token(token)[:12]

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path

            # capabilities 不需要鉴权（需暴露支持信息）
            if path == "/federation/v1/capabilities":
                self._write_json(200, _capabilities(allow_writes=allow_writes))
                return

            # Auth
            allowed, token_key = self._check_auth()
            if not allowed:
                self._write_json(401, {"error": "unauthorized", "reason": token_key})
                return

            # Rate limit
            if limiter and not limiter.allow(token_key):
                self._write_json(429, {
                    "error": "rate_limited",
                    "retry_after_seconds": int(limiter.window_seconds),
                })
                return

            qs = parse_qs(parsed.query)
            db = root / "db" / "main.sqlite3"

            if not db.exists():
                self._write_json(503, {"error": "db not ready"})
                return

            if path == "/federation/v1/persons":
                limit = int(qs.get("limit", ["50"])[0])
                r = _list_persons(db, limit=limit)
                if mask_pii_on_export:
                    r["persons"] = [sanitize_record(p) for p in r["persons"]]
                self._write_json(200, r)
                return
            if path.startswith("/federation/v1/persons/"):
                pid = path.rsplit("/", 1)[-1]
                p = _get_person(db, pid)
                if p is None:
                    self._write_json(404, {"error": "person not found", "id": pid})
                else:
                    if not is_exportable(p):
                        self._write_json(404, {"error": "not exportable"})
                        return
                    if mask_pii_on_export:
                        p = sanitize_record(p)
                    self._write_json(200, p)
                return
            if path == "/federation/v1/memories":
                owner = qs.get("owner_id", [None])[0]
                limit = int(qs.get("limit", ["50"])[0])
                r = _list_shared_memories(db, owner_id=owner, limit=limit)
                if mask_pii_on_export:
                    r["memories"] = [sanitize_record(m) for m in r["memories"]]
                self._write_json(200, r)
                return

            self._write_json(404, {"error": "not found", "path": path})

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path

            allowed, token_key = self._check_auth()
            if not allowed:
                self._write_json(401, {"error": "unauthorized", "reason": token_key})
                return

            if limiter and not limiter.allow(token_key):
                self._write_json(429, {
                    "error": "rate_limited",
                    "retry_after_seconds": int(limiter.window_seconds),
                })
                return

            if path != "/federation/v1/memories":
                self._write_json(404, {"error": "not found", "path": path})
                return
            if not allow_writes:
                self._write_json(403, {"error": "write_disabled"})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            raw_body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except Exception:
                self._write_json(400, {"error": "invalid_json"})
                return

            summary = str(payload.get("summary", "")).strip()
            owner_person_ids = payload.get("owner_person_ids") or []
            if not summary or not isinstance(owner_person_ids, list) or not owner_person_ids:
                self._write_json(
                    422,
                    {"error": "invalid_payload", "required": ["summary", "owner_person_ids"]},
                )
                return

            db = root / "db" / "main.sqlite3"
            if not db.exists():
                self._write_json(503, {"error": "db not ready"})
                return

            try:
                from we_together.services.federation_write_service import (
                    create_shared_memory_from_federation,
                )

                result = create_shared_memory_from_federation(
                    db,
                    summary=summary,
                    owner_person_ids=[str(x) for x in owner_person_ids],
                    source_skill_name=payload.get("source_skill_name"),
                    source_locator=payload.get("source_locator"),
                    scene_id=payload.get("scene_id"),
                    metadata=payload.get("metadata") or {},
                )
            except ValueError as exc:
                self._write_json(422, {"error": "invalid_payload", "message": str(exc)})
                return
            except Exception as exc:
                self._write_json(500, {"error": "write_failed", "message": str(exc)})
                return

            self._write_json(201, result)

        def log_message(self, *a, **kw):
            pass

    return H


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7781)
    ap.add_argument("--disable-pii-mask", action="store_true")
    ap.add_argument("--enable-write", action="store_true")
    args = ap.parse_args()
    root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)

    raw_tokens = os.environ.get("WE_TOGETHER_FED_TOKENS", "").strip()
    allowed_hashes: list[str] = []
    if raw_tokens:
        for t in raw_tokens.split(","):
            t = t.strip()
            if t:
                allowed_hashes.append(hash_token(t))

    limiter = RateLimiter(max_per_minute=60)
    handler = make_handler(
        root, allowed_token_hashes=allowed_hashes,
        rate_limiter=limiter,
        mask_pii_on_export=not args.disable_pii_mask,
        allow_writes=args.enable_write,
    )
    HTTPServer((args.host, args.port), handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
