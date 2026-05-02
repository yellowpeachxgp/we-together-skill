"""Phase 62 — Exemplar Scenarios (EX slices) + Phase 63 NT audit。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def test_scenario_runner_importable():
    import scenario_runner
    assert "family" in scenario_runner.SCENARIOS
    assert "work" in scenario_runner.SCENARIOS
    assert "book_club" in scenario_runner.SCENARIOS


def test_each_scenario_has_persons_and_narrations():
    import scenario_runner
    for name, spec in scenario_runner.SCENARIOS.items():
        assert len(spec["persons"]) >= 4, f"{name} too few persons"
        assert len(spec["narrations"]) >= 3, f"{name} too few narrations"


def test_run_scenario_family(temp_project_dir):
    import scenario_runner
    r = scenario_runner.run_scenario("family", temp_project_dir, archive=False)
    assert r["scenario"] == "family"
    assert r["persons_seeded"] == 4
    assert r["persons_count_after"] == 4
    assert r["events_created"] == 3
    assert r["memories_created"] == 3


def test_scenarios_archive_exists_in_examples():
    """跑过一次后 examples/scenarios/<name>/ 应存在"""
    for name in ("family", "work", "book_club"):
        d = REPO_ROOT / "examples" / "scenarios" / name
        if not d.exists():
            import pytest
            pytest.skip(f"{name} 尚未 archive（第一次 skip）")
        files = list(d.glob("run_*.json"))
        assert files, f"{name} archive 目录为空"


# --- Phase 63 NT audit ---

def test_all_adrs_have_status_frontmatter():
    """每份 ADR 必须在 frontmatter 里声明 status (不变式 #30)"""
    adr_dir = REPO_ROOT / "docs" / "superpowers" / "decisions"
    assert adr_dir.exists()
    missing: list[str] = []
    for md in sorted(adr_dir.glob("????-*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        # frontmatter 里有 status 或 `## 状态\n\nActive|Accepted|Superseded|Archived`
        head = text[:500].lower()
        if not any(tag in head for tag in ["status:", "## 状态", "## status"]):
            missing.append(md.name)
    assert not missing, f"ADR missing status: {missing}"


def test_no_invariant_without_test():
    """不变式 #29：每条不变式必须有 test_refs"""
    from we_together.invariants import INVARIANTS
    missing = [i.id for i in INVARIANTS if not i.test_refs]
    assert not missing, f"uncovered invariants: {missing}"


def test_migration_files_sequential():
    """migrations 应按 0001..NNNN 顺序无跳号（允许 skip 但不允许乱序）"""
    mig_dir = REPO_ROOT / "db" / "migrations"
    nums = sorted(
        int(m.stem.split("_", 1)[0])
        for m in mig_dir.glob("*.sql")
    )
    for prev, cur in zip(nums, nums[1:]):
        assert cur - prev <= 1, f"migration gap: {prev} → {cur}"


def test_selfintrospection_still_works():
    """#28 派生可重建 + #30 ADR 可 introspect 保持工作"""
    from we_together.services.self_introspection import self_describe
    d = self_describe()
    assert d["adrs_total"] > 0
    assert d["invariants_total"] == 28 or d["invariants_total"] == 29
    assert d["services_total"] >= 60
