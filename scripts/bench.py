"""性能基准：测 build_retrieval_package 和 dialogue_turn 的延迟百分位。

用法:
  .venv/bin/python scripts/bench.py --persons 100 --events 500 --memories 200 --runs 30
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
import tempfile
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.db.bootstrap import bootstrap_project
from we_together.runtime.sqlite_retrieval import (
    build_runtime_retrieval_package_from_db,
)
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch
from we_together.services.scene_service import add_scene_participant, create_scene


def _seed(root: Path, *, persons: int, events: int, memories: int):
    bootstrap_project(root)
    db_path = root / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    now_iso = datetime.now(UTC).isoformat()

    person_ids = []
    for i in range(persons):
        pid = f"person_b_{i}"
        conn.execute(
            """
            INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json,
                                created_at, updated_at)
            VALUES(?, ?, 'active', 0.8, '{}', ?, ?)
            """,
            (pid, f"P{i}", now_iso, now_iso),
        )
        person_ids.append(pid)

    for i in range(events):
        eid = f"evt_b_{i}"
        ts = (datetime.now(UTC) - timedelta(days=i % 30)).isoformat()
        conn.execute(
            """
            INSERT INTO events(event_id, event_type, source_type, timestamp, summary,
                               visibility_level, confidence, is_structured,
                               raw_evidence_refs_json, metadata_json, created_at)
            VALUES(?, 'dialogue_event', 'bench', ?, ?, 'visible', 0.8, 0, '[]', '{}', ?)
            """,
            (eid, ts, f"event {i}", now_iso),
        )
        conn.execute(
            "INSERT INTO event_participants(event_id, person_id, participant_role) VALUES(?, ?, 'speaker')",
            (eid, person_ids[i % persons]),
        )

    for i in range(memories):
        mid = f"mem_b_{i}"
        conn.execute(
            """
            INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
                                 confidence, is_shared, status, metadata_json,
                                 created_at, updated_at)
            VALUES(?, 'shared_memory', ?, 0.7, 0.7, 1, 'active', '{}', ?, ?)
            """,
            (mid, f"mem {i}", now_iso, now_iso),
        )
        conn.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) VALUES(?, 'person', ?, NULL)",
            (mid, person_ids[i % persons]),
        )

    conn.commit()
    conn.close()

    scene_id = create_scene(
        db_path=db_path, scene_type="private_chat", scene_summary="bench",
        environment={"location_scope": "remote", "channel_scope": "private_dm",
                     "visibility_scope": "mutual_visible"},
    )
    for pid in person_ids[:5]:
        add_scene_participant(db_path=db_path, scene_id=scene_id, person_id=pid,
                              activation_state="explicit", activation_score=0.9, is_speaking=False)
    return db_path, scene_id


def _time(fn, *, runs: int) -> dict:
    samples: list[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    samples.sort()
    return {
        "runs": runs,
        "min_ms": round(samples[0], 2),
        "p50_ms": round(statistics.median(samples), 2),
        "p95_ms": round(samples[int(0.95 * (runs - 1))], 2),
        "p99_ms": round(samples[int(0.99 * (runs - 1))], 2),
        "max_ms": round(samples[-1], 2),
    }


def run_bench(*, persons: int, events: int, memories: int, runs: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="wt-bench-") as tmp:
        root = Path(tmp)
        db_path, scene_id = _seed(root, persons=persons, events=events, memories=memories)

        # 1) build_retrieval_package (cold cache)
        def _build_cold():
            build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
        build_cold = _time(_build_cold, runs=runs)

        # 2) build_retrieval_package with cache hit
        def _build_warm():
            build_runtime_retrieval_package_from_db(
                db_path=db_path, scene_id=scene_id, input_hash="bench_hash",
            )
        # warm-up once
        _build_warm()
        build_warm = _time(_build_warm, runs=runs)

        # 3) apply a state patch
        def _apply():
            patch = build_patch(
                source_event_id=f"evt_bench_{uuid.uuid4().hex[:6]}",
                target_type="state",
                target_id=f"state_b_{uuid.uuid4().hex[:6]}",
                operation="update_state",
                payload={
                    "state_id": f"state_b_{uuid.uuid4().hex[:6]}",
                    "scope_type": "scene",
                    "scope_id": scene_id,
                    "state_type": "mood",
                    "value_json": {"mood": "x"},
                    "confidence": 0.7,
                },
                confidence=0.7,
                reason="bench",
            )
            apply_patch_record(db_path=db_path, patch=patch)
        apply = _time(_apply, runs=runs)

        return {
            "size": {"persons": persons, "events": events, "memories": memories},
            "build_retrieval_cold": build_cold,
            "build_retrieval_warm": build_warm,
            "apply_state_patch": apply,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="性能基准")
    parser.add_argument("--persons", type=int, default=100)
    parser.add_argument("--events", type=int, default=500)
    parser.add_argument("--memories", type=int, default=200)
    parser.add_argument("--runs", type=int, default=30)
    args = parser.parse_args()
    out = run_bench(
        persons=args.persons, events=args.events,
        memories=args.memories, runs=args.runs,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
