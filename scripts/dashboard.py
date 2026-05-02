"""scripts/dashboard.py — 最小 HTML + JSON 面板。

启动：
  python scripts/dashboard.py --root . --port 7780

路由：
  GET /            → HTML 面板
  GET /api/summary → JSON 摘要
  GET /api/tick    → JSON 近期 tick 记录
  GET /metrics     → Prometheus 文本
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.observability.metrics import export_prometheus_text
from we_together.services.tenant_router import infer_tenant_id_from_root, resolve_tenant_root

DASHBOARD_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>we-together dashboard</title>
<style>
 body { font-family: -apple-system, Segoe UI, sans-serif; margin: 24px; color:#222; }
 h1 { border-bottom: 1px solid #ccc; padding-bottom: 4px; }
 .card { display:inline-block; min-width:140px; margin:8px 12px 8px 0;
         padding:12px 16px; border:1px solid #ddd; border-radius:6px; }
 .card .v { font-size:28px; font-weight:600; }
 .card .k { color:#888; font-size:12px; text-transform:uppercase; }
 table { border-collapse: collapse; margin-top: 16px; }
 th, td { border: 1px solid #ddd; padding: 6px 12px; }
 small { color:#888; }
</style></head><body>
<h1>we-together · Social Graph Dashboard</h1>
<div id="summary">loading…</div>
<h2>Recent Ticks</h2>
<div id="ticks">loading…</div>
<p><small>/api/summary · /api/tick · /metrics</small></p>
<script>
async function load() {
  const s = await (await fetch('/api/summary')).json();
  document.getElementById('summary').innerHTML =
    Object.entries(s).map(([k,v])=>
      `<div class="card"><div class="k">${k}</div><div class="v">${v}</div></div>`
    ).join('');
  const t = await (await fetch('/api/tick')).json();
  const rows = t.ticks.map(r =>
    `<tr><td>${r.tick_index}</td><td>${r.started_at}</td>
     <td>${r.snapshot_id ?? '-'}</td>
     <td>${r.budget_exhausted ? 'yes' : 'no'}</td></tr>`
  ).join('');
  document.getElementById('ticks').innerHTML = rows
    ? `<table><tr><th>#</th><th>started</th><th>snapshot</th><th>budget</th></tr>${rows}</table>`
    : '<i>no ticks yet — run simulate_week.py</i>';
}
load();
</script></body></html>
"""


def _summary(root: Path) -> dict:
    db = root / "db" / "main.sqlite3"
    if not db.exists():
        return {"error": "db not found"}
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT (SELECT COUNT(*) FROM persons WHERE status='active'),"
            "(SELECT COUNT(*) FROM relations WHERE status='active'),"
            "(SELECT COUNT(*) FROM scenes WHERE status='active'),"
            "(SELECT COUNT(*) FROM events),"
            "(SELECT COUNT(*) FROM memories WHERE status='active'),"
            "(SELECT COUNT(*) FROM snapshots)"
        ).fetchone()
    finally:
        conn.close()
    return {
        "tenant_id": infer_tenant_id_from_root(root),
        "persons": row[0], "relations": row[1], "scenes": row[2],
        "events": row[3], "memories": row[4], "snapshots": row[5],
    }


def _recent_ticks(root: Path, limit: int = 10) -> dict:
    db = root / "db" / "main.sqlite3"
    if not db.exists():
        return {"ticks": []}
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT snapshot_id, summary, created_at "
            "FROM snapshots WHERE snapshot_id LIKE 'snap_tick_%' "
            "ORDER BY created_at DESC LIMIT ?", (int(limit),),
        ).fetchall()
    finally:
        conn.close()
    ticks = []
    for r in rows:
        snapshot_id = r[0]
        try:
            idx = int(snapshot_id.split("_")[2])
        except Exception:
            idx = -1
        ticks.append({
            "tick_index": idx,
            "started_at": r[2],
            "snapshot_id": snapshot_id,
            "budget_exhausted": False,
        })
    return {"ticks": ticks}


def make_handler(root: Path):
    class H(BaseHTTPRequestHandler):
        def _write(self, status: int, body: bytes, ct: str = "text/plain; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._write(200, DASHBOARD_HTML.encode("utf-8"),
                             "text/html; charset=utf-8")
            elif self.path == "/api/summary":
                self._write(200, json.dumps(_summary(root)).encode("utf-8"),
                             "application/json")
            elif self.path == "/api/tick":
                self._write(200, json.dumps(_recent_ticks(root)).encode("utf-8"),
                             "application/json")
            elif self.path == "/metrics":
                self._write(200, export_prometheus_text().encode("utf-8"),
                             "text/plain; version=0.0.4")
            else:
                self._write(404, b"not found")

        def log_message(self, *a, **kw):
            pass

    return H


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--port", type=int, default=7780)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    HTTPServer((args.host, args.port), make_handler(root)).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
