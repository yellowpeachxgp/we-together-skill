import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from seed_demo import seed_society_c  # noqa: E402

from we_together.errors import ConfigError  # noqa: E402
from we_together.eval.groundtruth_loader import load_groundtruth  # noqa: E402
from we_together.eval.llm_judge import build_fidelity_prompt, judge_fidelity  # noqa: E402
from we_together.eval.metrics import compute_precision_recall_f1  # noqa: E402
from we_together.eval.regression import (  # noqa: E402
    detect_regression,
    load_baseline,
    save_baseline,
)
from we_together.eval.relation_inference import evaluate_relation_inference  # noqa: E402
from we_together.llm.providers.mock import MockLLMClient  # noqa: E402


# --- metrics ---

def test_precision_recall_f1_basic():
    m = compute_precision_recall_f1({"a", "b", "c"}, {"b", "c", "d"})
    assert m["tp"] == 2 and m["fp"] == 1 and m["fn"] == 1
    assert m["precision"] == round(2/3, 4)
    assert m["recall"] == round(2/3, 4)


def test_precision_recall_empty_sets():
    m = compute_precision_recall_f1(set(), set())
    assert m["precision"] == 0.0 and m["recall"] == 0.0 and m["f1"] == 0.0


# --- groundtruth loader ---

def test_load_groundtruth_and_pairs():
    gt = load_groundtruth(REPO_ROOT / "benchmarks" / "society_c_groundtruth.json")
    assert gt.benchmark_name == "society_c_v1"
    pairs = gt.relation_pairs()
    assert ("Alice", "Bob", "work") in pairs


def test_load_groundtruth_missing_raises(tmp_path):
    import pytest
    with pytest.raises(ConfigError):
        load_groundtruth(tmp_path / "nope.json")


# --- relation_inference ---

def test_evaluate_relation_inference_on_society_c(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"
    gt_path = REPO_ROOT / "benchmarks" / "society_c_groundtruth.json"

    result = evaluate_relation_inference(db_path, gt_path)
    assert result["benchmark"] == "society_c_v1"
    assert result["precision"] >= 0.0
    assert result["recall"] >= 0.0
    assert isinstance(result["missing_pairs"], list)


# --- llm judge ---

def test_judge_fidelity_uses_llm_client():
    llm = MockLLMClient(scripted_json=[{
        "fidelity_score": 0.85, "missing_points": ["p1"], "fabrications": [],
    }])
    r = judge_fidelity(["源 1", "源 2"], "合并摘要", llm_client=llm)
    assert r["fidelity_score"] == 0.85
    assert r["missing_points"] == ["p1"]


def test_build_fidelity_prompt_contains_sources():
    msgs = build_fidelity_prompt(["源 A", "源 B"], "summary")
    assert any("源 A" in m.content for m in msgs)


# --- regression ---

def test_save_and_load_baseline(tmp_path):
    p = tmp_path / "baseline.json"
    save_baseline({"precision": 0.9, "recall": 0.8, "f1": 0.85}, p)
    loaded = load_baseline(p)
    assert loaded["precision"] == 0.9


def test_detect_regression_flags_big_drop():
    current = {"precision": 0.5, "recall": 0.8, "f1": 0.6}
    baseline = {"precision": 0.9, "recall": 0.8, "f1": 0.85}
    r = detect_regression(current, baseline, tolerance=0.05)
    assert not r["passed"]
    assert any(x["metric"] == "precision" for x in r["regressions"])


def test_detect_regression_tolerates_small_drop():
    current = {"precision": 0.87, "recall": 0.8, "f1": 0.83}
    baseline = {"precision": 0.9, "recall": 0.8, "f1": 0.85}
    r = detect_regression(current, baseline, tolerance=0.05)
    assert r["passed"]
