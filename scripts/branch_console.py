"""Branch 冲突裁决 mini-console — 基于 stdlib 的 HTTP 服务。

不依赖 fastapi 以避免外部依赖。访问:
  GET  /branches           → 列出 open local_branches + 每个的 candidates
  POST /resolve?branch_id=&candidate_id=
  GET  /                   → 简单 HTML

鉴权: 启动时 --token X 设置一个 bearer token，否则拒绝。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.db.connection import connect  # noqa: E402
from we_together.services.patch_applier import apply_patch_record  # noqa: E402
from we_together.services.patch_service import build_patch  # noqa: E402
from we_together.services.tenant_router import resolve_tenant_root  # noqa: E402


def resolve_branch_manually(db_path: Path, branch_id: str, candidate_id: str) -> dict:
    patch = build_patch(
        source_event_id=f"manual_resolve_{branch_id}",
        target_type="local_branch",
        target_id=branch_id,
        operation="resolve_local_branch",
        payload={
            "branch_id": branch_id,
            "selected_candidate_id": candidate_id,
            "status": "resolved",
            "reason": "manual resolution via branch console",
        },
        confidence=1.0,
        reason="manual resolution via branch console",
    )
    apply_patch_record(db_path=db_path, patch=patch)
    return {"resolved": True, "branch_id": branch_id, "candidate_id": candidate_id}


def list_open_branches(db_path: Path) -> list[dict]:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT branch_id, scope_type, scope_id, reason FROM local_branches "
        "WHERE status = 'open'"
    ).fetchall()
    out = []
    for r in rows:
        cands = conn.execute(
            "SELECT candidate_id, label, confidence, payload_json FROM branch_candidates "
            "WHERE branch_id = ?", (r["branch_id"],),
        ).fetchall()
        out.append({
            "branch_id": r["branch_id"],
            "scope_type": r["scope_type"],
            "scope_id": r["scope_id"],
            "reason": r["reason"],
            "candidates": [
                {"candidate_id": c["candidate_id"], "label": c["label"],
                 "score": c["confidence"]}
                for c in cands
            ],
        })
    conn.close()
    return out


def _make_handler(db_path: Path, token: str | None):
    class H(BaseHTTPRequestHandler):
        def _authorized(self) -> bool:
            if token is None:
                return True
            got = self.headers.get("Authorization", "")
            return got == f"Bearer {token}"

        def _send_json(self, code: int, body: dict | list) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            parsed = urlparse(self.path)
            if parsed.path == "/":
                html = (
                    "<html><body><h1>we-together branch console</h1>"
                    "<p>GET /branches to list. POST /resolve?branch_id=&candidate_id= to resolve.</p>"
                    "</body></html>"
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
                return
            if parsed.path == "/branches":
                self._send_json(200, list_open_branches(db_path))
                return
            self._send_json(404, {"error": "not_found"})

        def do_POST(self):
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            parsed = urlparse(self.path)
            if parsed.path == "/resolve":
                q = parse_qs(parsed.query)
                branch_id = (q.get("branch_id") or [None])[0]
                candidate_id = (q.get("candidate_id") or [None])[0]
                if not branch_id or not candidate_id:
                    self._send_json(400, {"error": "branch_id and candidate_id required"})
                    return
                try:
                    result = resolve_branch_manually(db_path=db_path, branch_id=branch_id,
                                                      candidate_id=candidate_id)
                    self._send_json(200, result)
                except Exception as exc:
                    self._send_json(500, {"error": str(exc)})
                return
            self._send_json(404, {"error": "not_found"})

        def log_message(self, *a, **kw):
            pass  # 静音

    return H


def serve(db_path: Path, host: str, port: int, token: str | None = None) -> HTTPServer:
    server = HTTPServer((host, port), _make_handler(db_path, token))
    return server


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--token", default=None)
    args = ap.parse_args()
    tenant_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    srv = serve(db_path, args.host, args.port, args.token)
    print(f"branch_console serving http://{args.host}:{args.port} db={db_path}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
