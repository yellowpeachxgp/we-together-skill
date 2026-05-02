"""Timeline CLI：打印一个 person 的事件/关系/persona_history 时序。"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.services.persona_history_service import query_history
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--person-id", required=True)
    ap.add_argument("--since", default=None, help="ISO 日期，只显示此后事件")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db = tenant_root / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)

    events_sql = """
        SELECT e.event_id, e.event_type, e.timestamp, e.summary
        FROM events e
        JOIN event_participants ep ON ep.event_id = e.event_id
        WHERE ep.person_id = ?
    """
    params: list = [args.person_id]
    if args.since:
        events_sql += " AND e.timestamp >= ?"
        params.append(args.since)
    events_sql += " ORDER BY e.timestamp DESC LIMIT ?"
    params.append(args.limit)

    events = [
        {"event_id": r[0], "event_type": r[1], "timestamp": r[2], "summary": r[3]}
        for r in conn.execute(events_sql, tuple(params)).fetchall()
    ]

    relations = [
        {"relation_id": r[0], "core_type": r[1], "strength": r[2]}
        for r in conn.execute(
            """SELECT DISTINCT r.relation_id, r.core_type, r.strength
               FROM relations r
               JOIN event_targets et ON et.target_type = 'relation' AND et.target_id = r.relation_id
               JOIN event_participants ep ON ep.event_id = et.event_id
               WHERE ep.person_id = ? AND r.status = 'active'""",
            (args.person_id,),
        ).fetchall()
    ]
    conn.close()

    try:
        history = query_history(db, args.person_id)
    except sqlite3.OperationalError:
        history = []

    print(json.dumps({
        "person_id": args.person_id,
        "persona_history": history,
        "active_relations": relations,
        "recent_events": events,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
