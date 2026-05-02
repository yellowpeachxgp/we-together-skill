"""activation_trace_service（Phase 40 NM）：记录与查询激活痕迹。

职责：
- record(from_id, to_id, weight, trace_type, ...)：一次激活边
- query_path(from_id, to_id, max_hops)：起点到终点的激活路径
- count_by_pair(from_id, to_id)：激活频率（用于可塑性）
- multi_hop_activation(start_id, max_hops, decay)：N 跳激活广度
- decay_traces(age_days)：删掉旧 trace（防表膨胀）
- apply_plasticity(db, base_strength_delta)：高频对 → relation.strength += ε

设计：
- 痕迹是**追加式**；不 update
- 可塑性是**显式调用**；不 hook 到 patch_applier（因为激活不等于语义变更）
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TraceRecord:
    from_entity_type: str
    from_entity_id: str
    to_entity_type: str
    to_entity_id: str
    weight: float = 1.0
    trace_type: str = "relation_traversal"
    hop_distance: int = 1
    scene_id: str | None = None


def record(
    db_path: Path, *,
    from_entity_type: str, from_entity_id: str,
    to_entity_type: str, to_entity_id: str,
    weight: float = 1.0,
    trace_type: str = "relation_traversal",
    hop_distance: int = 1,
    scene_id: str | None = None,
    metadata: dict | None = None,
) -> int:
    import json
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            """INSERT INTO activation_traces(from_entity_type, from_entity_id,
               to_entity_type, to_entity_id, weight, trace_type, hop_distance,
               scene_id, metadata_json, activated_at)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (from_entity_type, from_entity_id, to_entity_type, to_entity_id,
             float(weight), trace_type, int(hop_distance), scene_id,
             json.dumps(metadata or {}, ensure_ascii=False)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def record_batch(db_path: Path, traces: list[TraceRecord], *, scene_id: str | None = None) -> int:
    import json
    if not traces:
        return 0
    conn = sqlite3.connect(db_path)
    try:
        conn.executemany(
            """INSERT INTO activation_traces(from_entity_type, from_entity_id,
               to_entity_type, to_entity_id, weight, trace_type, hop_distance,
               scene_id, metadata_json, activated_at)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, '{}', datetime('now'))""",
            [(t.from_entity_type, t.from_entity_id,
              t.to_entity_type, t.to_entity_id,
              float(t.weight), t.trace_type, int(t.hop_distance),
              t.scene_id or scene_id) for t in traces],
        )
        conn.commit()
        return len(traces)
    finally:
        conn.close()


def count_by_pair(
    db_path: Path, *,
    from_entity_id: str, to_entity_id: str,
    since_days: int | None = None,
) -> int:
    conn = sqlite3.connect(db_path)
    try:
        if since_days is not None:
            row = conn.execute(
                """SELECT COUNT(*) FROM activation_traces
                   WHERE from_entity_id=? AND to_entity_id=?
                   AND activated_at >= datetime('now', ?)""",
                (from_entity_id, to_entity_id, f"-{int(since_days)} days"),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) FROM activation_traces "
                "WHERE from_entity_id=? AND to_entity_id=?",
                (from_entity_id, to_entity_id),
            ).fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def query_path(
    db_path: Path, *, from_entity_id: str, to_entity_id: str, max_hops: int = 3,
) -> list[list[dict]]:
    """返回从 from 到 to 的所有 ≤ max_hops 的激活路径（每条是 edge 序列）。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT from_entity_id AS f, to_entity_id AS t, weight AS w,
               trace_type AS tt, hop_distance AS hd
               FROM activation_traces""",
        ).fetchall()
    finally:
        conn.close()

    adj: dict[str, list[dict]] = {}
    for r in rows:
        adj.setdefault(r["f"], []).append({
            "to": r["t"], "weight": r["w"],
            "trace_type": r["tt"], "hop": r["hd"],
        })

    paths: list[list[dict]] = []

    def dfs(node: str, depth: int, acc: list[dict], visited: set):
        if depth > max_hops:
            return
        if node == to_entity_id and acc:
            paths.append(list(acc))
            return
        for edge in adj.get(node, []):
            if edge["to"] in visited:
                continue
            visited.add(edge["to"])
            acc.append({"from": node, **edge})
            dfs(edge["to"], depth + 1, acc, visited)
            acc.pop()
            visited.discard(edge["to"])

    dfs(from_entity_id, 0, [], {from_entity_id})
    return paths


def multi_hop_activation(
    db_path: Path, *, start_entity_id: str, max_hops: int = 3, decay: float = 0.5,
) -> dict[str, float]:
    """从 start 广度优先发散 N 跳，每跳衰减 decay 倍；返回 {entity_id: cumulative_weight}"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT from_entity_id AS f, to_entity_id AS t, weight AS w "
            "FROM activation_traces",
        ).fetchall()
    finally:
        conn.close()

    adj: dict[str, list[tuple[str, float]]] = {}
    for r in rows:
        adj.setdefault(r["f"], []).append((r["t"], r["w"]))

    visited: dict[str, float] = {start_entity_id: 1.0}
    frontier: list[tuple[str, float, int]] = [(start_entity_id, 1.0, 0)]
    while frontier:
        node, w, hop = frontier.pop(0)
        if hop >= max_hops:
            continue
        for (nbr, ew) in adj.get(node, []):
            new_w = w * ew * decay
            if nbr in visited and visited[nbr] >= new_w:
                continue
            visited[nbr] = max(visited.get(nbr, 0.0), new_w)
            frontier.append((nbr, new_w, hop + 1))
    return visited


def decay_traces(db_path: Path, *, age_days: int = 90) -> int:
    """删除早于 age_days 天的 trace，返回删除条数。"""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "DELETE FROM activation_traces WHERE activated_at < datetime('now', ?)",
            (f"-{int(age_days)} days",),
        )
        n = cur.rowcount
        conn.commit()
        return n
    finally:
        conn.close()


def apply_plasticity(
    db_path: Path, *, min_count: int = 3, strength_delta: float = 0.02,
    max_strength: float = 1.0, since_days: int = 30,
) -> dict:
    """激活频率 >= min_count 的 person-person 对 → 对应 relation.strength += ε。

    不新建 relation；仅对已存在的 active relation 生效（避免激活噪声凭空造关系）。
    Relation 与 person 的关联通过 entity_links(from_type='relation', relation_type='participant')。
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    updated = 0
    details: list[dict] = []
    try:
        rows = conn.execute(
            """SELECT from_entity_id, to_entity_id, COUNT(*) AS cnt
               FROM activation_traces
               WHERE from_entity_type='person' AND to_entity_type='person'
               AND activated_at >= datetime('now', ?)
               GROUP BY from_entity_id, to_entity_id
               HAVING cnt >= ?""",
            (f"-{int(since_days)} days", int(min_count)),
        ).fetchall()

        for r in rows:
            # 找包含这两个 person 的 active relation
            # entity_links: from_type='relation', relation_type='participant', to=person
            rel_rows = conn.execute(
                """SELECT DISTINCT r.relation_id, r.strength
                   FROM relations r
                   JOIN entity_links e1 ON e1.from_type='relation'
                     AND e1.from_id=r.relation_id
                     AND e1.relation_type='participant'
                     AND e1.to_type='person'
                     AND e1.to_id=?
                   JOIN entity_links e2 ON e2.from_type='relation'
                     AND e2.from_id=r.relation_id
                     AND e2.relation_type='participant'
                     AND e2.to_type='person'
                     AND e2.to_id=?
                   WHERE r.status='active'""",
                (r["from_entity_id"], r["to_entity_id"]),
            ).fetchall()
            for rel in rel_rows:
                new_s = min(max_strength, (rel["strength"] or 0.0) + strength_delta)
                if new_s == rel["strength"]:
                    continue
                conn.execute(
                    "UPDATE relations SET strength=?, updated_at=datetime('now') "
                    "WHERE relation_id=?",
                    (new_s, rel["relation_id"]),
                )
                updated += 1
                details.append({
                    "relation_id": rel["relation_id"],
                    "old_strength": rel["strength"], "new_strength": new_s,
                    "activation_count": r["cnt"],
                })
        conn.commit()
    finally:
        conn.close()
    return {"updated": updated, "details": details}


def recent_traces(db_path: Path, *, limit: int = 20) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT from_entity_type, from_entity_id, to_entity_type, to_entity_id,
               weight, trace_type, hop_distance, scene_id, activated_at
               FROM activation_traces ORDER BY activated_at DESC LIMIT ?""",
            (int(limit),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
