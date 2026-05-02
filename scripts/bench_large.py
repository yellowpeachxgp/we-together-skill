"""scripts/bench_large.py：大规模压测脚手架。

为保持测试环境快速，默认只插入 10_000 person（非真 10 万）。CLI 参数可调大。
测量三项：
  - bulk_insert_persons_seconds
  - retrieval_cold_ms_p50/p95
  - retrieval_warm_ms_p50/p95
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.db.bootstrap import bootstrap_project  # noqa: E402
from we_together.runtime.sqlite_retrieval import (  # noqa: E402
    build_runtime_retrieval_package_from_db,
)
from we_together.services.scene_service import (  # noqa: E402
    add_scene_participant,
    create_scene,
)
from we_together.services.tenant_router import resolve_tenant_root  # noqa: E402


def _insert_persons(db_path: Path, count: int) -> float:
    conn = sqlite3.connect(db_path)
    t0 = time.time()
    conn.executemany(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) "
        "VALUES(?, ?, 'active', 0.8, '{}', datetime('now'), datetime('now'))",
        [(f"p_bench_{uuid.uuid4().hex[:10]}", f"P{i}") for i in range(count)],
    )
    conn.commit()
    elapsed = time.time() - t0
    conn.close()
    return elapsed


def _bench_retrieval(db_path: Path, scene_id: str, reps: int) -> dict:
    cold: list[float] = []
    warm: list[float] = []
    for i in range(reps):
        input_hash = f"h_{i}"
        t0 = time.time()
        build_runtime_retrieval_package_from_db(
            db_path=db_path, scene_id=scene_id, input_hash=input_hash,
        )
        cold.append((time.time() - t0) * 1000)
    for i in range(reps):
        input_hash = f"h_{i}"
        t0 = time.time()
        build_runtime_retrieval_package_from_db(
            db_path=db_path, scene_id=scene_id, input_hash=input_hash,
        )
        warm.append((time.time() - t0) * 1000)
    return {
        "reps": reps,
        "cold_ms_p50": statistics.median(cold),
        "cold_ms_p95": sorted(cold)[int(len(cold) * 0.95)],
        "warm_ms_p50": statistics.median(warm),
        "warm_ms_p95": sorted(warm)[int(len(warm) * 0.95)],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--persons", type=int, default=10_000)
    ap.add_argument("--reps", type=int, default=20)
    args = ap.parse_args()

    project_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    bootstrap_project(project_root)
    db_path = project_root / "db" / "main.sqlite3"

    bulk_secs = _insert_persons(db_path, args.persons)

    # 准备 scene
    scene_id = create_scene(
        db_path=db_path, scene_type="work_discussion", scene_summary="bench scene",
        environment={"location_scope": "remote", "channel_scope": "group_channel",
                     "visibility_scope": "group_visible"},
    )
    # 取前 5 个 person 作为 participants
    c = sqlite3.connect(db_path)
    pids = [r[0] for r in c.execute("SELECT person_id FROM persons LIMIT 5").fetchall()]
    c.close()
    for pid in pids:
        add_scene_participant(
            db_path=db_path, scene_id=scene_id, person_id=pid,
            activation_state="explicit", activation_score=1.0, is_speaking=False,
        )

    bench = _bench_retrieval(db_path, scene_id, args.reps)
    report = {
        "persons_inserted": args.persons,
        "bulk_insert_seconds": round(bulk_secs, 3),
        "retrieval": bench,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
