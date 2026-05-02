"""Phase 58 — 不变式→测试映射 (IN slices)。

每条不变式必须在 invariants.INVARIANTS 里挂 test_refs，
且 test_refs 指向的测试在仓库里真实存在（不变式 #29）。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def test_invariants_registered_28_items():
    from we_together.invariants import INVARIANTS
    assert len(INVARIANTS) == 28
    ids = [inv.id for inv in INVARIANTS]
    assert ids == list(range(1, 29))


def test_every_invariant_has_title_and_description():
    from we_together.invariants import INVARIANTS
    for inv in INVARIANTS:
        assert inv.title.strip()
        assert inv.description.strip()


def test_every_invariant_has_adr_ref():
    from we_together.invariants import INVARIANTS
    for inv in INVARIANTS:
        assert inv.adr_refs, f"invariant #{inv.id} missing ADR ref"


def test_every_invariant_has_at_least_one_test_ref():
    """不变式 #29：纸面不变式禁止——每条必须有 >= 1 测试。"""
    from we_together.invariants import INVARIANTS
    for inv in INVARIANTS:
        assert inv.test_refs, (
            f"invariant #{inv.id} ({inv.title}) has no test coverage; "
            "见不变式 #29"
        )


def test_coverage_summary_100_percent():
    from we_together.invariants import coverage_summary
    s = coverage_summary()
    assert s["total_invariants"] == 28
    assert s["coverage_ratio"] == 1.0
    assert s["uncovered"] == 0


def test_test_refs_point_to_existing_files():
    """每个 test_ref 的 file 必须存在。"""
    from we_together.invariants import INVARIANTS
    missing: list[str] = []
    for inv in INVARIANTS:
        for ref in inv.test_refs:
            path_part = ref.split("::")[0]
            if not (REPO_ROOT / path_part).exists():
                missing.append(f"#{inv.id}: {ref}")
    assert not missing, f"missing test files: {missing}"


def test_get_invariant_single():
    from we_together.invariants import get_invariant
    inv26 = get_invariant(26)
    assert inv26 is not None
    assert "时间范围" in inv26.title or "时间" in inv26.description


def test_get_invariant_none_for_invalid():
    from we_together.invariants import get_invariant
    assert get_invariant(999) is None
    assert get_invariant(0) is None


def test_list_as_dicts_serializable():
    import json
    from we_together.invariants import list_as_dicts
    items = list_as_dicts()
    text = json.dumps(items, ensure_ascii=False)
    assert "persona_summary" in text or "派生" in text


def test_every_adr_ref_format_valid():
    import re
    from we_together.invariants import INVARIANTS
    pattern = re.compile(r"^ADR \d{4}$")
    for inv in INVARIANTS:
        for r in inv.adr_refs:
            assert pattern.match(r), f"bad ADR ref format: {r!r}"


def test_every_test_ref_format_valid():
    """格式: tests/path::test_name"""
    from we_together.invariants import INVARIANTS
    for inv in INVARIANTS:
        for r in inv.test_refs:
            assert r.startswith("tests/"), r
            assert "::" in r, r


def test_no_duplicate_invariant_ids():
    from we_together.invariants import INVARIANTS
    ids = [i.id for i in INVARIANTS]
    assert len(ids) == len(set(ids))


def test_no_duplicate_titles():
    from we_together.invariants import INVARIANTS
    titles = [i.title for i in INVARIANTS]
    # 允许部分相似但核心不重复
    assert len(titles) == len(set(titles))


def test_invariants_phase_labels_valid():
    """每条不变式的 phase 字段非空"""
    from we_together.invariants import INVARIANTS
    for inv in INVARIANTS:
        assert inv.phase, f"invariant #{inv.id} missing phase label"


def test_get_all_invariants_returns_copy():
    from we_together.invariants import INVARIANTS, get_all_invariants
    result = get_all_invariants()
    assert len(result) == len(INVARIANTS)
    # 允许改引用但不应改核心表（我们返回 list() 副本）
    result.clear()
    assert len(INVARIANTS) == 28


def test_invariant_meta_all_phase_groups_present():
    """确保 P1 / P8-12 / P13-17 / P18-21 / P22-24 / P25-27 / P29 / P30 / P33 / P34 /
    P40 / P41 / P44 / P45 / P48 / P51 / P52 / P55 都有代表"""
    from we_together.invariants import INVARIANTS
    phases = {i.phase for i in INVARIANTS}
    expected_phases = {
        "P1", "P8-12", "P13-17", "P18-21", "P22-24", "P25-27",
        "P29", "P30", "P33", "P34", "P40", "P41", "P44", "P45",
        "P48", "P51", "P52", "P55",
    }
    missing = expected_phases - phases
    assert not missing, f"missing phases: {missing}"
