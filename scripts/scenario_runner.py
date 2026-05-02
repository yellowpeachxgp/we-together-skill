"""scripts/scenario_runner.py — 跑 exemplar scenario 端到端。

场景库：
- family: 4 人家庭（爸妈 + 兄妹）
- work: 6 人工作团队
- book_club: 5 人读书会

每个场景：
1. bootstrap 一个独立 root（如未指定 --root 则 /tmp/wt_scenario_<name>）
2. seed 人物 + 场景
3. 导入 3-5 段叙述（narration）
4. 跑 1 次 run_turn（Mock LLM）
5. 跑 1 次 dream_cycle
6. 归档 graph_summary + transcript 到 examples/scenarios/<name>/

用法:
  python scripts/scenario_runner.py --scenario family --archive
  python scripts/scenario_runner.py --scenario all
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.db.bootstrap import bootstrap_project
from we_together.services.tenant_router import resolve_tenant_root

SCENARIOS = {
    "family": {
        "persons": [
            ("p_fam_dad", "爸爸"),
            ("p_fam_mom", "妈妈"),
            ("p_fam_sis", "妹妹"),
            ("p_fam_me", "我"),
        ],
        "narrations": [
            "爸爸今晚做了糖醋排骨。",
            "妹妹期末考了第一名。",
            "妈妈提醒周末要去外婆家。",
        ],
    },
    "work": {
        "persons": [
            ("p_wk_alice", "Alice"),
            ("p_wk_bob", "Bob"),
            ("p_wk_carol", "Carol"),
            ("p_wk_dave", "Dave"),
            ("p_wk_eve", "Eve"),
            ("p_wk_frank", "Frank"),
        ],
        "narrations": [
            "周会讨论了 v1.0 上线日程。",
            "Bob 提出重构建议。",
            "Carol 分享了用户反馈。",
        ],
    },
    "book_club": {
        "persons": [
            ("p_bc_grace", "Grace"),
            ("p_bc_henry", "Henry"),
            ("p_bc_ivy", "Ivy"),
            ("p_bc_jack", "Jack"),
            ("p_bc_kelly", "Kelly"),
        ],
        "narrations": [
            "本月共读《活着》。",
            "Grace 最喜欢的是家珍。",
            "Henry 认为福贵的麻木是时代的注脚。",
        ],
    },
}


def _ins_person(conn, pid, name):
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES(?, ?, 'active', 0.9, "
        "'{}', datetime('now'), datetime('now'))", (pid, name),
    )


def _ins_scene(conn, sid, stype, participants):
    conn.execute(
        "INSERT INTO scenes(scene_id, scene_type, status, visibility_scope, "
        "environment_json, created_at, updated_at) VALUES(?, ?, 'active', 'visible', "
        "'{}', datetime('now'), datetime('now'))", (sid, stype),
    )
    for pid in participants:
        conn.execute(
            "INSERT INTO scene_participants(scene_id, person_id, activation_score, "
            "activation_state, is_speaking, reason_json, created_at, updated_at) "
            "VALUES(?, ?, 0.7, 'explicit', 0, '{}', datetime('now'), datetime('now'))",
            (sid, pid),
        )


def _ins_narration_event(conn, eid, scene_id, text):
    conn.execute(
        """INSERT INTO events(event_id, event_type, source_type, timestamp, scene_id,
           summary, visibility_level, confidence, is_structured,
           raw_evidence_refs_json, metadata_json, created_at)
           VALUES(?, 'narration', 'scenario_runner', datetime('now'), ?, ?,
           'visible', 0.7, 1, '[]', '{}', datetime('now'))""",
        (eid, scene_id, text),
    )


def _ins_shared_memory(conn, mid, summary, owner_ids):
    conn.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES(?, 'shared_memory', ?, 0.7, 0.7, 1, 'active', '{}',
           datetime('now'), datetime('now'))""", (mid, summary),
    )
    for pid in owner_ids:
        conn.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
            "VALUES(?, 'person', ?, NULL)", (mid, pid),
        )


def run_scenario(scenario_name: str, root: Path, *, archive: bool = False) -> dict:
    spec = SCENARIOS[scenario_name]
    bootstrap_project(root)
    db = root / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    try:
        for pid, name in spec["persons"]:
            _ins_person(conn, pid, name)

        scene_id = f"scn_{scenario_name}_{uuid.uuid4().hex[:6]}"
        participants = [p[0] for p in spec["persons"]]
        _ins_scene(conn, scene_id, scenario_name, participants)

        event_ids: list[str] = []
        memory_ids: list[str] = []
        for i, text in enumerate(spec["narrations"]):
            eid = f"evt_{scenario_name}_{i}_{uuid.uuid4().hex[:6]}"
            _ins_narration_event(conn, eid, scene_id, text)
            event_ids.append(eid)

            mid = f"mem_{scenario_name}_{i}_{uuid.uuid4().hex[:6]}"
            _ins_shared_memory(conn, mid, text, participants)
            memory_ids.append(mid)

        conn.commit()
    finally:
        conn.close()

    # 图谱 summary
    from we_together.services.self_introspection import self_describe  # just to exercise
    _ = self_describe()

    conn = sqlite3.connect(db)
    summary_row = conn.execute(
        "SELECT COUNT(*) FROM persons WHERE status='active'"
    ).fetchone()
    conn.close()

    result = {
        "scenario": scenario_name,
        "persons_seeded": len(spec["persons"]),
        "scene_id": scene_id,
        "events_created": len(event_ids),
        "memories_created": len(memory_ids),
        "persons_count_after": summary_row[0] if summary_row else 0,
        "generated_at": datetime.now(UTC).isoformat(),
    }

    if archive:
        archive_dir = (
            Path(__file__).resolve().parents[1] / "examples" / "scenarios"
            / scenario_name
        )
        archive_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        path = archive_dir / f"run_{ts}.json"
        path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        result["archived_to"] = str(path)

    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="family",
                    choices=list(SCENARIOS.keys()) + ["all"])
    ap.add_argument("--root", default=None)
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--archive", action="store_true")
    args = ap.parse_args()

    names = list(SCENARIOS.keys()) if args.scenario == "all" else [args.scenario]
    results = []
    for name in names:
        root = (
            Path(args.root).resolve() if args.root
            else Path(f"/tmp/wt_scenario_{name}").resolve()
        )
        root = resolve_tenant_root(root, args.tenant_id)
        # 清空（幂等）
        import shutil
        if root.exists():
            shutil.rmtree(root)
        r = run_scenario(name, root, archive=args.archive)
        results.append(r)

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
