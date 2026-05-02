"""Graph analytics：图谱结构指标 — 中心度 / 群体密度 / 孤立识别 / associative 联想。"""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path

from we_together.db.connection import connect


def compute_degree_centrality(db_path: Path) -> list[dict]:
    """每个 active person 的度数：参与 event_participants 中关联 relation 的不同对方人数。"""
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT p.person_id, p.primary_name,
                  (SELECT COUNT(DISTINCT ep_other.person_id)
                   FROM event_participants ep_self
                   JOIN event_targets et ON et.event_id = ep_self.event_id
                        AND et.target_type = 'relation'
                   JOIN event_participants ep_other
                        ON ep_other.event_id = ep_self.event_id
                        AND ep_other.person_id != p.person_id
                   WHERE ep_self.person_id = p.person_id) AS degree
           FROM persons p
           WHERE p.status = 'active'
           ORDER BY degree DESC"""
    ).fetchall()
    conn.close()
    return [{"person_id": r["person_id"], "primary_name": r["primary_name"],
              "degree": r["degree"]} for r in rows]


def compute_group_density(db_path: Path) -> list[dict]:
    """每个 group 的密度：group_members 两两组合中，实际有 relation 的比例。"""
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    groups = conn.execute(
        "SELECT group_id, name FROM groups WHERE status = 'active'"
    ).fetchall()
    results = []
    for g in groups:
        members = [r["person_id"] for r in conn.execute(
            "SELECT person_id FROM group_members WHERE group_id = ? AND status = 'active'",
            (g["group_id"],),
        ).fetchall()]
        n = len(members)
        if n < 2:
            results.append({"group_id": g["group_id"], "name": g["name"],
                             "member_count": n, "density": 0.0})
            continue
        # 计算两两中有多少存在 relation
        pair_count = n * (n - 1) / 2
        # 对每对：是否有 event_targets.relation 包含两人
        connected = 0
        for i in range(n):
            for j in range(i + 1, n):
                row = conn.execute(
                    """SELECT 1 FROM event_targets et
                       JOIN event_participants ep1 ON ep1.event_id = et.event_id
                            AND ep1.person_id = ?
                       JOIN event_participants ep2 ON ep2.event_id = et.event_id
                            AND ep2.person_id = ?
                       WHERE et.target_type = 'relation'
                       LIMIT 1""",
                    (members[i], members[j]),
                ).fetchone()
                if row:
                    connected += 1
        density = connected / pair_count if pair_count > 0 else 0.0
        results.append({"group_id": g["group_id"], "name": g["name"],
                         "member_count": n, "pair_count": int(pair_count),
                         "connected": connected, "density": round(density, 3)})
    conn.close()
    return results


def identify_isolated_persons(db_path: Path, *, window_days: int = 30) -> list[dict]:
    """近 window_days 无任何 event 参与的 active person。"""
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT p.person_id, p.primary_name
           FROM persons p
           WHERE p.status = 'active'
             AND NOT EXISTS (
               SELECT 1 FROM event_participants ep
               JOIN events e ON e.event_id = ep.event_id
               WHERE ep.person_id = p.person_id
                 AND e.timestamp > datetime('now', '-' || ? || ' days')
             )""",
        (window_days,),
    ).fetchall()
    conn.close()
    return [{"person_id": r["person_id"], "primary_name": r["primary_name"]}
             for r in rows]


def full_report(db_path: Path, *, window_days: int = 30) -> dict:
    return {
        "degree": compute_degree_centrality(db_path)[:10],
        "group_density": compute_group_density(db_path),
        "isolated_persons": identify_isolated_persons(db_path, window_days=window_days),
    }
