import json
from pathlib import Path

from we_together.eval.condenser_eval import run_condense_eval
from we_together.eval.persona_drift_eval import run_persona_drift_eval
from we_together.llm.providers.mock import MockLLMClient

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_condense_eval_all_pass():
    bench = REPO_ROOT / "benchmarks" / "condense_groundtruth.json"
    llm = MockLLMClient(default_json={
        "fidelity_score": 0.85, "missing_points": [], "fabrications": [],
    })
    r = run_condense_eval(bench, llm_client=llm)
    assert r["total"] == 2
    assert r["passed"] == 2
    assert r["pass_rate"] == 1.0


def test_condense_eval_one_fails():
    bench = REPO_ROOT / "benchmarks" / "condense_groundtruth.json"
    llm = MockLLMClient(scripted_json=[
        {"fidelity_score": 0.9},
        {"fidelity_score": 0.3, "missing_points": ["月份"], "fabrications": []},
    ])
    r = run_condense_eval(bench, llm_client=llm)
    assert r["passed"] == 1
    assert r["pass_rate"] == 0.5


def test_persona_drift_eval():
    bench = REPO_ROOT / "benchmarks" / "persona_drift_groundtruth.json"
    llm = MockLLMClient(default_json={"fidelity_score": 0.75})
    r = run_persona_drift_eval(
        bench,
        generated_persona_by_case={"pd_alice_work_shift": "技术领导者"},
        llm_client=llm,
    )
    assert r["total"] == 1
    assert r["passed"] == 1


def test_benchmark_files_load():
    for name in ("society_c", "society_d", "society_work",
                 "condense", "persona_drift", "multimodal"):
        p = REPO_ROOT / "benchmarks" / f"{name}_groundtruth.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "benchmark_name" in data
