"""Phase 23 IT-1 端到端真集成测试。

跑全链路：bootstrap → seed → graph_summary → import → snapshot →
rollback → replay → dialogue → eval-relation。全程不 mock 基础设施，只
对 LLM 客户端 mock（保持离线）。
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))


@pytest.fixture
def full_stack(temp_project_dir):
    """真 bootstrap + seed_society_c 的完整项目。"""
    from seed_demo import seed_society_c
    summary = seed_society_c(temp_project_dir)
    return temp_project_dir, summary


def test_bootstrap_seed_produces_graph(full_stack):
    root, summary = full_stack
    db = root / "db" / "main.sqlite3"
    assert db.exists()
    c = sqlite3.connect(db)
    persons = c.execute("SELECT COUNT(*) FROM persons WHERE status='active'").fetchone()[0]
    relations = c.execute("SELECT COUNT(*) FROM relations WHERE status='active'").fetchone()[0]
    scenes = c.execute("SELECT COUNT(*) FROM scenes WHERE status='active'").fetchone()[0]
    c.close()
    assert persons == 8 and relations >= 5 and scenes == 3


def test_narration_ingest_then_rollback(full_stack):
    root, summary = full_stack
    db = root / "db" / "main.sqlite3"

    from we_together.services.ingestion_service import ingest_narration
    r = ingest_narration(db_path=db, text="小明 和 小强 今天一起做项目",
                          source_name="test_integration")
    assert r.get("event_id") or r.get("import_job_id")

    # 记录当前 event_count
    c = sqlite3.connect(db)
    n_before = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    c.close()
    assert n_before > 5

    # 取最新 snapshot 并回滚
    from we_together.services.snapshot_service import (
        list_snapshots,
        rollback_to_snapshot,
    )
    snaps = list_snapshots(db)
    assert len(snaps) >= 1
    target = snaps[-1]["snapshot_id"]
    rollback_to_snapshot(db, target)
    # 回滚不应丢 seed 数据（seed 在 target 之前）
    c = sqlite3.connect(db)
    persons_after = c.execute("SELECT COUNT(*) FROM persons WHERE status='active'").fetchone()[0]
    c.close()
    assert persons_after >= 8


def test_dialogue_turn_with_mock_llm(full_stack):
    root, summary = full_stack
    db = root / "db" / "main.sqlite3"
    scene_id = summary["scenes"]["work"]

    from we_together.llm.providers.mock import MockLLMClient
    from we_together.services.chat_service import run_turn

    llm = MockLLMClient(default_content="好的，我了解了。")
    result = run_turn(
        db_path=db, scene_id=scene_id, user_input="你们下周有安排吗？",
        llm_client=llm, adapter_name="openai_compat",
    )
    assert result["response"]["text"] == "好的，我了解了。"
    assert result["event_id"]


def test_eval_relation_baseline_passes(full_stack):
    root, summary = full_stack
    db = root / "db" / "main.sqlite3"

    from we_together.eval.relation_inference import evaluate_relation_inference
    gt_path = REPO_ROOT / "benchmarks" / "society_c_groundtruth.json"
    result = evaluate_relation_inference(db, gt_path)
    # seed_society_c 应该 precision/recall 都 >= 0.9
    assert result["precision"] >= 0.9
    assert result["recall"] >= 0.9


def test_cli_dispatch_alive():
    """we-together CLI 入口基本健康。"""
    from we_together.cli import VERSION, main
    code = main(["version"])
    assert code == 0
    assert VERSION


def test_federation_end_to_end(temp_project_with_migrations, tmp_path):
    """register ref → write remote stub → fetch_eager_refs → inject。"""
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.federation_fetcher import (
        build_default_fetcher,
        inject_eager_into_participants,
    )
    from we_together.services.federation_service import register_external_person

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    register_external_person(db, external_skill_name="partner",
                              external_person_id="ext_1",
                              display_name="Partner", policy="eager",
                              trust_level=0.8)
    fdir = tmp_path / "federation" / "partner"
    fdir.mkdir(parents=True)
    (fdir / "ext_1.json").write_text(json.dumps({
        "display_name": "Partner Remote",
        "persona_summary": "协作同事",
    }))
    f = build_default_fetcher(tmp_path)
    fetched = f.fetch_eager_refs(db)
    assert len(fetched) == 1 and fetched[0]["fetched"]

    pkg = {"participants": [{"person_id": "local_a"}]}
    inject_eager_into_participants(pkg, fetched)
    assert len(pkg["participants"]) == 2
    assert pkg["participants"][1]["remote"] is True
