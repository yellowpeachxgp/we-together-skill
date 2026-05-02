"""time_series_svg（Phase 49 UX-4/5）：纯 SVG 时序图 + 趋势数据。

无第三方依赖；直接返回 SVG 字符串，可嵌入 dashboard HTML。
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path


def _day_key(ts: str) -> str:
    if not ts:
        return ""
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(ts)
    except Exception:
        return ""
    return d.astimezone(UTC).strftime("%Y-%m-%d")


def memory_growth_trend(db_path: Path, *, days: int = 30) -> list[tuple[str, int]]:
    """过去 N 天每天新增 memory 数。"""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """SELECT DATE(created_at) AS d, COUNT(*) FROM memories
               WHERE created_at >= datetime('now', ?)
               GROUP BY DATE(created_at) ORDER BY d""",
            (f"-{int(days)} days",),
        ).fetchall()
    finally:
        conn.close()
    return [(r[0], r[1]) for r in rows]


def event_count_trend(db_path: Path, *, days: int = 30) -> list[tuple[str, int]]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """SELECT DATE(timestamp) AS d, COUNT(*) FROM events
               WHERE timestamp >= datetime('now', ?)
               GROUP BY DATE(timestamp) ORDER BY d""",
            (f"-{int(days)} days",),
        ).fetchall()
    finally:
        conn.close()
    return [(r[0], r[1]) for r in rows]


def render_sparkline_svg(
    points: list[tuple[str, int]], *,
    width: int = 300, height: int = 60,
    stroke: str = "#4a90e2", fill: str = "#eef4fb",
    title: str = "",
) -> str:
    """渲染极简 sparkline。points = [(label, value), ...]"""
    if not points:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
            f'<text x="8" y="{height//2}" font-size="12" fill="#888">no data</text>'
            f'</svg>'
        )
    values = [p[1] for p in points]
    vmax = max(values) if values else 1
    vmin = min(values)
    span = max(1, vmax - vmin)
    n = len(points)
    step = (width - 10) / max(1, n - 1)
    coords = []
    for i, v in enumerate(values):
        x = 5 + i * step
        y = height - 5 - ((v - vmin) / span) * (height - 15)
        coords.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(coords)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'role="img" aria-label="{title}">',
    ]
    # 填充区
    svg.append(
        f'<polyline fill="{fill}" stroke="none" '
        f'points="5,{height-5} {poly} {width-5},{height-5}" />'
    )
    # 折线
    svg.append(
        f'<polyline fill="none" stroke="{stroke}" stroke-width="1.5" '
        f'points="{poly}" />'
    )
    # 标题
    if title:
        svg.append(
            f'<text x="8" y="14" font-size="11" fill="#666">{title}</text>'
        )
    # 最新值
    last_v = values[-1]
    svg.append(
        f'<text x="{width-4}" y="{height-8}" font-size="10" '
        f'fill="#333" text-anchor="end">{last_v}</text>'
    )
    svg.append("</svg>")
    return "".join(svg)


def trend_bundle(db_path: Path, *, days: int = 30) -> dict:
    memory = memory_growth_trend(db_path, days=days)
    events = event_count_trend(db_path, days=days)
    return {
        "memory": memory,
        "events": events,
        "memory_svg": render_sparkline_svg(
            memory, title=f"memory growth ({days}d)",
        ),
        "events_svg": render_sparkline_svg(
            events, title=f"events ({days}d)", stroke="#e28f4a", fill="#fbf0e6",
        ),
    }
