"""scripts/seed_society_m.py — 合成 50 人社会（medium scale）。

生成：
- 50 persons（混合工作/家庭/朋友面）
- ~150 relations（work / family / friendship 各 50）
- ~300 memories（shared + individual）
- ~500 events
- 10 scenes

用法:
  python scripts/seed_society_m.py --root . [--n 50]
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.db.bootstrap import bootstrap_project
from we_together.services.tenant_router import resolve_tenant_root

NAMES = [
    "Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Henry",
    "Ivy", "Jack", "Kelly", "Liam", "Mona", "Noah", "Olivia", "Paul",
    "Quinn", "Ruby", "Sam", "Tina", "Uma", "Victor", "Wendy", "Xavier",
    "Yara", "Zane", "Amy", "Ben", "Cathy", "Dan", "Ella", "Fred",
    "Gina", "Hugo", "Iris", "Jake", "Kim", "Leo", "Mia", "Nick",
    "Opal", "Pete", "Quila", "Rose", "Stan", "Tara", "Una", "Vern",
    "Will", "Xena",
]

CORE_TYPES = ["work", "family", "friendship", "intimacy", "authority"]


def _ins_person(conn, pid: str, name: str, conf: float = 0.8) -> None:
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES(?, ?, 'active', ?, '{}', "
        "datetime('now'), datetime('now'))", (pid, name, conf),
    )


def _ins_relation(conn, rid: str, core: str, strength: float) -> None:
    conn.execute(
        "INSERT INTO relations(relation_id, core_type, status, strength, "
        "confidence, metadata_json, created_at, updated_at) VALUES(?, ?, 'active', "
        "?, 0.7, '{}', datetime('now'), datetime('now'))",
        (rid, core, strength),
    )


def _ins_rel_participant(conn, rid: str, pid: str) -> None:
    conn.execute(
        "INSERT INTO entity_links(from_type, from_id, relation_type, to_type, to_id, "
        "weight, metadata_json) VALUES('relation', ?, 'participant', 'person', ?, "
        "1.0, '{}')", (rid, pid),
    )


def _ins_memory(conn, mid: str, summary: str, owner_ids: list[str], shared: bool = True) -> None:
    conn.execute(
        "INSERT INTO memories(memory_id, memory_type, summary, relevance_score, "
        "confidence, is_shared, status, metadata_json, created_at, updated_at) "
        "VALUES(?, ?, ?, ?, 0.7, ?, 'active', '{}', datetime('now'), datetime('now'))",
        (mid, "shared_memory" if shared else "individual_memory", summary,
         random.uniform(0.3, 0.9), 1 if shared else 0),
    )
    for pid in owner_ids:
        conn.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
            "VALUES(?, 'person', ?, NULL)", (mid, pid),
        )


def _ins_event(conn, eid: str, summary: str) -> None:
    conn.execute(
        "INSERT INTO events(event_id, event_type, source_type, timestamp, summary, "
        "visibility_level, confidence, is_structured, raw_evidence_refs_json, "
        "metadata_json, created_at) VALUES(?, 'narration', 'seed', datetime('now'), "
        "?, 'visible', 0.7, 1, '[]', '{}', datetime('now'))",
        (eid, summary),
    )


def _ins_scene(conn, sid: str, stype: str, participants: list[str]) -> None:
    conn.execute(
        "INSERT INTO scenes(scene_id, scene_type, status, visibility_scope, "
        "environment_json, created_at, updated_at) VALUES(?, ?, 'active', 'visible', "
        "'{}', datetime('now'), datetime('now'))", (sid, stype),
    )
    for pid in participants:
        conn.execute(
            "INSERT INTO scene_participants(scene_id, person_id, activation_score, "
            "activation_state, is_speaking, reason_json, created_at, updated_at) "
            "VALUES(?, ?, ?, 'explicit', 0, '{}', datetime('now'), datetime('now'))",
            (sid, pid, random.uniform(0.3, 0.9)),
        )


def seed(root: Path, *, n: int = 50, seed_value: int = 42) -> dict:
    random.seed(seed_value)
    bootstrap_project(root)
    db = root / "db" / "main.sqlite3"

    persons: list[tuple[str, str]] = []
    for i in range(n):
        pid = f"p_m_{i}_{uuid.uuid4().hex[:6]}"
        name = NAMES[i % len(NAMES)] + (f"_{i}" if i >= len(NAMES) else "")
        persons.append((pid, name))

    conn = sqlite3.connect(db)
    try:
        for pid, name in persons:
            _ins_person(conn, pid, name)

        # 关系：每个 person 平均 3 个 relation
        relations: list[str] = []
        for i, (pid, _) in enumerate(persons):
            for _ in range(3):
                target = persons[random.randrange(len(persons))][0]
                if target == pid:
                    continue
                rid = f"r_m_{uuid.uuid4().hex[:10]}"
                core = random.choice(CORE_TYPES)
                _ins_relation(conn, rid, core, random.uniform(0.3, 0.8))
                _ins_rel_participant(conn, rid, pid)
                _ins_rel_participant(conn, rid, target)
                relations.append(rid)

        # 记忆：每人 6 条
        memories: list[str] = []
        for pid, name in persons:
            for j in range(6):
                mid = f"m_m_{uuid.uuid4().hex[:10]}"
                owners = [pid]
                shared = (j % 2 == 0)
                if shared:
                    extra = persons[random.randrange(len(persons))][0]
                    if extra != pid:
                        owners.append(extra)
                summary = f"{name} 的记忆 #{j}"
                _ins_memory(conn, mid, summary, owners, shared=shared)
                memories.append(mid)

        # 事件：10 * n
        events = []
        for i in range(10 * n):
            eid = f"e_m_{uuid.uuid4().hex[:10]}"
            _ins_event(conn, eid, f"event #{i}")
            events.append(eid)

        # Scenes：10 个
        scene_ids: list[str] = []
        for k in range(10):
            sid = f"s_m_{k}_{uuid.uuid4().hex[:6]}"
            stype = random.choice(["work_meeting", "family_dinner", "friends_hangout"])
            participants = [p[0] for p in random.sample(persons, min(8, len(persons)))]
            _ins_scene(conn, sid, stype, participants)
            scene_ids.append(sid)

        conn.commit()
    finally:
        conn.close()

    return {
        "persons": len(persons),
        "relations": len(relations),
        "memories": len(memories),
        "events": len(events),
        "scenes": len(scene_ids),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed-value", type=int, default=42)
    args = ap.parse_args()
    tenant_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    r = seed(tenant_root, n=args.n, seed_value=args.seed_value)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
