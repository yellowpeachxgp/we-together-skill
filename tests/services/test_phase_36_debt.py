"""Phase 36 — 规模 & 债务 (DT slices)。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def test_vector_index_backend_validation():
    from we_together.services.vector_index import SUPPORTED_BACKENDS, _resolve_backend
    assert _resolve_backend("auto") == "flat_python"
    assert _resolve_backend("flat_python") == "flat_python"
    assert "sqlite_vec" in SUPPORTED_BACKENDS
    assert "faiss" in SUPPORTED_BACKENDS


def test_vector_index_unknown_backend_raises():
    import pytest

    from we_together.services.vector_index import _resolve_backend
    with pytest.raises(ValueError, match="unknown backend"):
        _resolve_backend("qdrant")


def test_vector_index_sqlite_vec_delayed_import_raises_if_missing():
    """若 sqlite_vec 未装，要用 sqlite_vec backend 会 raise RuntimeError（留 v0.15）"""
    import pytest
    try:
        import sqlite_vec  # noqa: F401
        pytest.skip("sqlite_vec installed, skip negative test")
    except ImportError:
        from we_together.services.vector_index import _require_sqlite_vec
        with pytest.raises(RuntimeError, match="sqlite_vec not installed"):
            _require_sqlite_vec()


def test_vector_index_faiss_delayed_import_raises_if_missing():
    import pytest
    try:
        import faiss  # noqa: F401
        pytest.skip("faiss installed, skip negative test")
    except ImportError:
        from we_together.services.vector_index import _require_faiss
        with pytest.raises(RuntimeError, match="faiss not installed"):
            _require_faiss()


def test_skill_runtime_schema_version_constant():
    """不变式 #19: 版本号是稳定常量"""
    from we_together.runtime.skill_runtime import SKILL_SCHEMA_VERSION
    assert SKILL_SCHEMA_VERSION == "1"


def test_service_inventory_doc_exists():
    p = REPO_ROOT / "docs" / "superpowers" / "state" / "2026-04-19-service-inventory.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Service Inventory" in text
    # 核对 recall 三路径与 relation 三路径的合流判定已写入
    assert "三条 recall 职责" in text
    assert "三条 relation 职责" in text


def test_migration_audit_doc_exists():
    p = REPO_ROOT / "docs" / "superpowers" / "state" / "2026-04-19-migration-audit.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    # 确认覆盖全部 0001-0015
    for mig in ["0001_initial", "0007_cold_memories", "0010_event_causality",
                "0012_perceived_memory", "0015_media_assets"]:
        assert mig in text


def test_llm_providers_delayed_import():
    """provider import 不应在 import 阶段 require 真 SDK（ADR 0027 不变式 #15）"""
    # MockLLMClient 必定可用（不依赖 SDK）
    from we_together.llm.providers.mock import MockLLMClient
    c = MockLLMClient(default_content="x")
    assert c is not None


def test_bench_scale_script_importable():
    """bench_scale 脚本可 import；不触发大规模 seed"""
    import importlib.util
    p = REPO_ROOT / "scripts" / "bench_scale.py"
    spec = importlib.util.spec_from_file_location("bench_scale", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.seed_synthetic)
    assert callable(mod.main)


def test_vector_index_build_with_explicit_flat_python(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.vector_index import VectorIndex
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    idx = VectorIndex.build(db, target="memory", backend="flat_python")
    assert idx.backend == "flat_python"


def test_bench_scale_supports_backend_flag(temp_project_with_migrations, monkeypatch, capsys):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    monkeypatch.setattr(
        "sys.argv",
        [
            "bench_scale.py",
            "--root",
            str(temp_project_with_migrations),
            "--n",
            "2",
            "--queries",
            "1",
            "--backend",
            "flat_python",
        ],
    )
    import bench_scale

    rc = bench_scale.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert '"backend": "flat_python"' in out
