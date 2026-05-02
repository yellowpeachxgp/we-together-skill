from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from we_together.db.bootstrap import bootstrap_project
from we_together.llm.providers.embedding import MockEmbeddingClient
from we_together.services.vector_index import VectorIndex
from we_together.services.vector_similarity import encode_vec


def _load_bench_module():
    p = REPO_ROOT / "scripts" / "bench_scale.py"
    spec = importlib.util.spec_from_file_location("bench_scale_phase_65", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _seed_memory_embeddings(db: Path, texts: list[str], *, prefix: str) -> MockEmbeddingClient:
    client = MockEmbeddingClient(dim=16)
    conn = sqlite3.connect(db)
    now = datetime.now(UTC).isoformat()
    for i, text in enumerate(texts):
        mid = f"{prefix}_{i}"
        conn.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
               confidence, is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?, 'shared_memory', ?, 0.7, 0.7, 1, 'active', '{}', ?, ?)""",
            (mid, text, now, now),
        )
        vec = client.embed([text])[0]
        conn.execute(
            """INSERT INTO memory_embeddings(memory_id, model_name, dim, vec, created_at)
               VALUES(?, ?, ?, ?, ?)""",
            (mid, client.provider, client.dim, encode_vec(vec), now),
        )
    conn.commit()
    conn.close()
    return client


def test_bench_scale_build_report_includes_runtime_metadata():
    mod = _load_bench_module()
    report = mod.build_report(
        backend="sqlite_vec",
        n_seeded=100,
        dim=32,
        seed_s=0.12,
        build_s=0.34,
        index_size=100,
        queries=5,
        query_total_s=0.01,
    )
    assert report["backend"] == "sqlite_vec"
    assert report["n_seeded"] == 100
    assert "platform" in report
    assert "python_version" in report


def test_bench_scale_archive_report_writes_backend_file(tmp_path):
    mod = _load_bench_module()
    report = mod.build_report(
        backend="faiss",
        n_seeded=100000,
        dim=32,
        seed_s=0.12,
        build_s=0.34,
        index_size=100000,
        queries=5,
        query_total_s=0.01,
    )
    out = mod.archive_report(report, tmp_path / "benchmarks" / "scale")
    assert out.exists()
    assert "faiss" in out.name
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["backend"] == "faiss"
    assert payload["n_seeded"] == 100000


def test_bench_scale_supports_archive_flag(temp_project_with_migrations, monkeypatch, capsys):
    bootstrap_project(temp_project_with_migrations)
    mod = _load_bench_module()
    monkeypatch.setattr(
        "sys.argv",
        [
            "bench_scale.py",
            "--root",
            str(temp_project_with_migrations),
            "--n",
            "20",
            "--queries",
            "2",
            "--backend",
            "flat_python",
            "--archive",
        ],
    )
    rc = mod.main()
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["backend"] == "flat_python"
    assert "archived_to" in out


def test_real_sqlite_vec_backend_if_installed(temp_project_with_migrations):
    pytest.importorskip("sqlite_vec")
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    client = _seed_memory_embeddings(db, ["project alpha", "family dinner", "travel log"], prefix="m_sql_real")
    idx = VectorIndex.build(db, target="memory", backend="sqlite_vec")
    q_vec = client.embed(["project alpha"])[0]
    result = idx.query(q_vec, k=1)
    assert idx.backend == "sqlite_vec"
    assert result[0][0] == "m_sql_real_0"


def test_real_faiss_backend_if_installed(temp_project_with_migrations):
    pytest.importorskip("faiss")
    pytest.importorskip("numpy")
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    client = _seed_memory_embeddings(db, ["project beta", "concert night", "gym note"], prefix="m_faiss_real")
    idx = VectorIndex.build(db, target="memory", backend="faiss")
    q_vec = client.embed(["project beta"])[0]
    result = idx.query(q_vec, k=1)
    assert idx.backend == "faiss"
    assert result[0][0] == "m_faiss_real_0"
