from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_bench_module():
    p = REPO_ROOT / "scripts" / "bench_scale.py"
    spec = importlib.util.spec_from_file_location("bench_scale_phase_66", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_compare_report_has_winner_fields():
    mod = _load_bench_module()
    compare = mod.build_compare_report(
        n_seeded=100000,
        dim=32,
        queries=30,
        reports=[
            {
                "backend": "flat_python",
                "per_query_ms": 88.1,
                "qps": 11.3,
                "index_size": 100000,
            },
            {
                "backend": "sqlite_vec",
                "per_query_ms": 7.2,
                "qps": 138.8,
                "index_size": 100000,
            },
            {
                "backend": "faiss",
                "per_query_ms": 1.3,
                "qps": 769.2,
                "index_size": 100000,
            },
        ],
    )
    assert compare["mode"] == "compare"
    assert compare["n_seeded"] == 100000
    assert compare["fastest_backend"] == "faiss"
    assert compare["highest_qps_backend"] == "faiss"
    assert len(compare["reports"]) == 3


def test_archive_compare_report_writes_compare_file(tmp_path):
    mod = _load_bench_module()
    compare = mod.build_compare_report(
        n_seeded=1000,
        dim=16,
        queries=10,
        reports=[
            {"backend": "flat_python", "per_query_ms": 9.1, "qps": 100.0, "index_size": 1000},
            {"backend": "sqlite_vec", "per_query_ms": 2.1, "qps": 400.0, "index_size": 1000},
        ],
    )
    path = mod.archive_compare_report(compare, tmp_path / "benchmarks" / "scale")
    assert path.exists()
    assert "bench_compare_1k" in path.name
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["mode"] == "compare"
    assert payload["fastest_backend"] == "sqlite_vec"


def test_bench_scale_backend_all_runs_compare_mode(temp_project_dir, monkeypatch, capsys):
    mod = _load_bench_module()

    fake_reports = {
        "flat_python": {"backend": "flat_python", "n_seeded": 100, "dim": 16, "queries": 2, "per_query_ms": 10.0, "qps": 100.0, "index_size": 100},
        "sqlite_vec": {"backend": "sqlite_vec", "n_seeded": 100, "dim": 16, "queries": 2, "per_query_ms": 4.0, "qps": 250.0, "index_size": 100},
        "faiss": {"backend": "faiss", "n_seeded": 100, "dim": 16, "queries": 2, "per_query_ms": 1.5, "qps": 666.7, "index_size": 100},
    }

    monkeypatch.setattr(
        mod,
        "run_single_benchmark",
        lambda root, *, n, dim, queries, backend: dict(fake_reports[backend]),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "bench_scale.py",
            "--root",
            str(temp_project_dir),
            "--n",
            "100",
            "--dim",
            "16",
            "--queries",
            "2",
            "--backend",
            "all",
        ],
    )
    rc = mod.main()
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["mode"] == "compare"
    assert out["fastest_backend"] == "faiss"
    assert [r["backend"] for r in out["reports"]] == ["flat_python", "sqlite_vec", "faiss"]


def test_backend_all_uses_isolated_temp_roots(temp_project_dir, monkeypatch):
    mod = _load_bench_module()
    seen_roots: list[Path] = []

    def _fake_run(root, *, n, dim, queries, backend):
        seen_roots.append(Path(root))
        return {
            "backend": backend,
            "n_seeded": n,
            "dim": dim,
            "queries": queries,
            "per_query_ms": 1.0,
            "qps": 1000.0,
            "index_size": n,
        }

    monkeypatch.setattr(mod, "run_single_benchmark", _fake_run)
    compare = mod.run_all_benchmarks(temp_project_dir, n=100, dim=16, queries=2)
    assert compare["mode"] == "compare"
    assert len(seen_roots) == 3
    assert all(root != temp_project_dir for root in seen_roots)


def test_compare_archive_100k_exists_in_repo():
    archive = REPO_ROOT / "benchmarks" / "scale"
    files = sorted(archive.glob("bench_compare_100k_*.json"))
    assert files, "expected compare 100k archive"
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    assert payload["mode"] == "compare"
    assert payload["n_seeded"] == 100000
    assert payload["fastest_backend"] in {"flat_python", "sqlite_vec", "faiss"}
    assert len(payload["reports"]) == 3


def test_compare_archive_1m_exists_in_repo():
    archive = REPO_ROOT / "benchmarks" / "scale"
    files = sorted(archive.glob("bench_compare_1m_*.json"))
    assert files, "expected compare 1m archive"
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    assert payload["mode"] == "compare"
    assert payload["n_seeded"] == 1_000_000
    assert payload["highest_qps_backend"] in {"flat_python", "sqlite_vec", "faiss"}
    assert len(payload["reports"]) == 3


def test_scale_bench_v2_report_exists():
    p = REPO_ROOT / "docs" / "superpowers" / "state" / "2026-04-19-scale-bench-v2-report.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "100,000" in text or "100000" in text
    assert "1,000,000" in text or "1000000" in text
    assert "faiss" in text.lower()
