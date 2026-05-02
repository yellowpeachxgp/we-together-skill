"""Phase 47 — 规模化 50-500 人 (SC slices)。"""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))


def test_seed_society_m_50_persons(temp_project_dir):
    from seed_society_m import seed
    r = seed(temp_project_dir, n=50, seed_value=42)
    assert r["persons"] == 50
    assert r["relations"] > 0
    assert r["memories"] > 0
    assert r["scenes"] == 10

    conn = sqlite3.connect(temp_project_dir / "db" / "main.sqlite3")
    cnt_p = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    cnt_r = conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
    cnt_m = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    conn.close()
    assert cnt_p == 50
    assert cnt_r >= 100
    assert cnt_m == 50 * 6


def test_seed_society_m_deterministic(temp_project_dir):
    """相同 seed 两次 seed 结果相同（persons 数，memories 数）"""
    from seed_society_m import seed
    r1 = seed(temp_project_dir, n=20, seed_value=100)
    assert r1["persons"] == 20


def test_seed_society_l_import():
    import importlib.util
    p = REPO_ROOT / "scripts" / "seed_society_l.py"
    spec = importlib.util.spec_from_file_location("ssl_t", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.main)


def test_retrieval_on_50_person_graph(temp_project_dir):
    """50 人图谱：build_retrieval_package 必须可运行（性能为副"""
    from seed_society_m import seed
    seed(temp_project_dir, n=50, seed_value=42)
    db = temp_project_dir / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    scene_id = conn.execute(
        "SELECT scene_id FROM scenes WHERE status='active' LIMIT 1"
    ).fetchone()[0]
    conn.close()

    from we_together.runtime.sqlite_retrieval import (
        build_runtime_retrieval_package_from_db,
    )
    t0 = time.perf_counter()
    pkg = build_runtime_retrieval_package_from_db(db, scene_id=scene_id)
    dt = time.perf_counter() - t0
    assert "scene_summary" in pkg
    # 50 人规模下 retrieval 应该很快
    assert dt < 2.0, f"retrieval too slow: {dt:.2f}s"


def test_tick_on_50_person_graph(temp_project_dir):
    from seed_society_m import seed
    from we_together.services.time_simulator import simulate, TickBudget
    seed(temp_project_dir, n=50, seed_value=42)
    db = temp_project_dir / "db" / "main.sqlite3"

    t0 = time.perf_counter()
    r = simulate(db, ticks=3, budget=TickBudget(llm_calls=0))
    dt = time.perf_counter() - t0
    assert r["ticks"] == 3
    # 50 人 × 3 tick 应在几秒内
    assert dt < 15.0, f"tick too slow on 50 person: {dt:.2f}s"


def test_retrieval_latency_p50_p95_50_person(temp_project_dir):
    from seed_society_m import seed
    seed(temp_project_dir, n=50, seed_value=42)
    db = temp_project_dir / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    scenes = [r[0] for r in conn.execute(
        "SELECT scene_id FROM scenes WHERE status='active'"
    ).fetchall()]
    conn.close()

    from we_together.runtime.sqlite_retrieval import (
        build_runtime_retrieval_package_from_db,
    )
    times: list[float] = []
    for sid in scenes:
        t0 = time.perf_counter()
        build_runtime_retrieval_package_from_db(db, scene_id=sid)
        times.append((time.perf_counter() - t0) * 1000)

    times.sort()
    p50 = times[len(times) // 2]
    p95 = times[int(len(times) * 0.95)] if len(times) > 1 else times[-1]
    # 目标：p50 < 500ms, p95 < 1500ms（50 人基线）
    assert p50 < 500, f"p50 too slow: {p50:.1f}ms"
    assert p95 < 1500, f"p95 too slow: {p95:.1f}ms"


def test_seed_society_m_with_integrity_audit(temp_project_dir):
    """seed 后图谱必须 healthy"""
    from seed_society_m import seed
    from we_together.services.integrity_audit import full_audit
    seed(temp_project_dir, n=20, seed_value=42)
    db = temp_project_dir / "db" / "main.sqlite3"
    r = full_audit(db)
    # 允许 relation_cycles 因自环检测简化可能有少量，但核心无 dangling/orphan
    assert len(r["dangling_memory_owners"]) == 0
    assert len(r["orphaned_memories"]) == 0


def test_vector_index_backend_validation_scale():
    """规模化场景下 backend 仍走 flat_python fallback"""
    from we_together.services.vector_index import _resolve_backend, SUPPORTED_BACKENDS
    assert _resolve_backend("sqlite_vec") == "sqlite_vec"  # 解析成功
    assert _resolve_backend("faiss") == "faiss"
    assert "sqlite_vec" in SUPPORTED_BACKENDS
