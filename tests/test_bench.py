from pathlib import Path
import sys

# 复用 scripts/bench.py 的 run_bench
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from bench import run_bench  # noqa: E402


def test_bench_runs_on_small_dataset():
    result = run_bench(persons=5, events=20, memories=10, runs=3)
    assert result["build_retrieval_cold"]["runs"] == 3
    assert result["build_retrieval_cold"]["p50_ms"] > 0
    assert result["apply_state_patch"]["runs"] == 3
