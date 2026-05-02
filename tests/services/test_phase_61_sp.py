"""Phase 61 — 规模化真压测 (SP slices)。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def test_scale_archive_exists():
    archive = REPO_ROOT / "benchmarks" / "scale"
    if not archive.exists():
        import pytest
        pytest.skip("scale archive dir 不存在（首次会 skip）")
    files = list(archive.glob("bench_*.json"))
    assert files, "期望至少一份 scale bench 归档"


def test_scale_archive_10k_format():
    archive = REPO_ROOT / "benchmarks" / "scale"
    files = sorted(archive.glob("bench_10k_*.json"))
    if not files:
        import pytest
        pytest.skip("no 10k bench yet")
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["n_seeded"] == 10000
    assert "per_query_ms" in data
    assert "qps" in data
    # index_size 可能略小（部分 embedding 失败）或等于
    assert data["index_size"] >= 9000


def test_scale_archive_50k_format():
    archive = REPO_ROOT / "benchmarks" / "scale"
    files = sorted(archive.glob("bench_50k_*.json"))
    if not files:
        import pytest
        pytest.skip("no 50k bench yet")
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["n_seeded"] == 50000
    assert data["per_query_ms"] > 0


def test_vector_index_backends_still_available():
    """不变式：sqlite_vec/faiss 作为 backend 选项继续存在（stub）"""
    from we_together.services.vector_index import SUPPORTED_BACKENDS
    assert "sqlite_vec" in SUPPORTED_BACKENDS
    assert "faiss" in SUPPORTED_BACKENDS


def test_scale_report_exists():
    p = REPO_ROOT / "docs" / "superpowers" / "state" / "2026-04-19-scale-bench-report.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "10,000" in text or "10000" in text
    assert "50,000" in text or "50000" in text
