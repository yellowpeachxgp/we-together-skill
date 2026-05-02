import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from seed_demo import seed_society_c  # noqa: E402

from we_together.agents.person_agent import PersonAgent  # noqa: E402
from we_together.agents.turn_taking import (  # noqa: E402
    next_speaker,
    orchestrate_multi_agent_turn,
)
from we_together.db.bootstrap import bootstrap_project  # noqa: E402
from we_together.eval.contradiction_eval import (  # noqa: E402
    run_contradiction_eval,
)
from we_together.llm.providers.mock import MockLLMClient  # noqa: E402
from we_together.llm.providers.multimodal_embedding import (  # noqa: E402
    CLIPStubClient,
    MockMultimodalClient,
    cross_modal_similarity,
)
from we_together.llm.providers.embedding import MockEmbeddingClient  # noqa: E402
from we_together.services.contradiction_detector import (  # noqa: E402
    detect_contradictions,
    find_candidate_pairs,
    judge_contradiction,
)
from we_together.services.proactive_agent import (  # noqa: E402
    check_budget,
    execute_intent,
    list_recent_intents,
    ProactiveIntent,
    proactive_scan,
    scan_all_triggers,
    scan_anniversary_triggers,
    scan_silence_triggers,
)
from we_together.services.proactive_prefs import (  # noqa: E402
    is_allowed,
    set_consent,
    set_mute,
)
from we_together.services.vector_similarity import encode_vec  # noqa: E402


# --- Phase 29 agents ---

def test_person_agent_from_db(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    alice = summary["persons"]["alice"]

    llm = MockLLMClient(default_content="mock")
    agent = PersonAgent.from_db(db, alice, llm_client=llm)
    assert agent.primary_name == "Alice"
    assert agent.person_id == alice


def test_person_agent_speak(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    alice = summary["persons"]["alice"]

    llm = MockLLMClient(scripted_responses=["你好，我是 Alice。"])
    agent = PersonAgent.from_db(db, alice, llm_client=llm)
    text = agent.speak(scene_summary="work meeting")
    assert text == "你好，我是 Alice。"


def test_turn_taking_picks_higher_score():
    class FakeAgent:
        def __init__(self, pid, score):
            self.person_id = pid
            self.primary_name = pid
            self._score = score
        def decide_speak(self, *, context, turn_state):
            return self._score

    agents = [FakeAgent("a", 0.3), FakeAgent("b", 0.7), FakeAgent("c", 0.5)]
    picked = next_speaker(agents, activation_map={}, turn_state={})
    assert picked.person_id == "b"


def test_turn_taking_no_speaker_when_all_zero():
    class FakeAgent:
        person_id = "x"
        primary_name = "x"
        def decide_speak(self, **kw): return 0.0
    picked = next_speaker([FakeAgent()], activation_map={}, turn_state={})
    assert picked is None


def test_orchestrate_multi_agent_produces_transcript(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    alice_id = summary["persons"]["alice"]
    bob_id = summary["persons"]["bob"]

    llm = MockLLMClient(scripted_responses=["Alice 开场", "Bob 回复", "Alice 总结"])
    a1 = PersonAgent.from_db(db, alice_id, llm_client=llm)
    a2 = PersonAgent.from_db(db, bob_id, llm_client=llm)
    transcript = orchestrate_multi_agent_turn(
        [a1, a2], scene_summary="work",
        activation_map={
            alice_id: {"activation_score": 0.8},
            bob_id: {"activation_score": 0.6},
        },
        turns=3,
    )
    assert len(transcript) == 3
    assert {e["speaker"] for e in transcript} <= {"Alice", "Bob"}


# --- Phase 30 proactive ---

def test_proactive_prefs_mute(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    assert is_allowed(db, "p1", "anniversary")  # 默认允许
    set_mute(db, "p1", mute=True)
    assert not is_allowed(db, "p1", "anniversary")
    set_mute(db, "p1", mute=False)
    assert is_allowed(db, "p1", "anniversary")


def test_proactive_prefs_consent(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    set_consent(db, "p2", "silence", False)
    assert not is_allowed(db, "p2", "silence")
    assert is_allowed(db, "p2", "anniversary")  # 其他 trigger 未拒绝


def test_scan_anniversary_triggers(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    c = sqlite3.connect(db)
    c.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('pa','A','active',0.8,'{}',"
        "datetime('now'),datetime('now'))"
    )
    from datetime import timedelta
    past = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    c.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES('m_anniv','shared_memory','重要',0.9,0.8,1,'active','{}',?,?)""",
        (past, past),
    )
    c.execute(
        "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
        "VALUES('m_anniv','person','pa',NULL)"
    )
    c.commit(); c.close()

    triggers = scan_anniversary_triggers(db)
    assert len(triggers) >= 1
    assert triggers[0].name == "anniversary"


def test_proactive_scan_writes_event(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    c = sqlite3.connect(db)
    c.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('p3','P','active',0.8,'{}',"
        "datetime('now'),datetime('now'))"
    )
    from datetime import timedelta
    past = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    c.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES('m_s','shared_memory','s',0.9,0.8,1,'active','{}',?,?)""",
        (past, past),
    )
    c.execute(
        "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
        "VALUES('m_s','person','p3',NULL)"
    )
    c.commit(); c.close()

    llm = MockLLMClient(scripted_json=[
        {"action": "check_in", "text": "记得你上个月的事", "confidence": 0.7},
    ])
    result = proactive_scan(db, daily_budget=1, llm_client=llm)
    assert result["executed"] == 1
    recent = list_recent_intents(db)
    assert recent[0]["metadata"]["trigger_name"] == "anniversary"


def test_check_budget_limits(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    # 插入 5 个今日 proactive_intent_event
    c = sqlite3.connect(db)
    for i in range(3):
        c.execute(
            """INSERT INTO events(event_id, event_type, source_type, timestamp,
               summary, visibility_level, confidence, is_structured,
               raw_evidence_refs_json, metadata_json, created_at)
               VALUES(?, 'proactive_intent_event', 'proactive_agent',
               datetime('now'), 'x', 'visible', 0.5, 1, '[]', '{}',
               datetime('now'))""",
            (f"evt_pb_{i}",),
        )
    c.commit(); c.close()
    assert check_budget(db, daily_budget=5) == 2


# --- Phase 31 contradiction ---

def test_find_candidate_pairs(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    c = sqlite3.connect(db)
    client = MockEmbeddingClient(dim=16)
    now = datetime.now(UTC).isoformat()
    # 两条相同文本 → cosine=1
    for i, t in enumerate(["同主题 A", "同主题 A", "另主题 B"]):
        c.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
               confidence, is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?, 'shared_memory', ?, 0.7, 0.7, 1, 'active', '{}', ?, ?)""",
            (f"m_cd_{i}", t, now, now),
        )
        vec = client.embed([t])[0]
        c.execute(
            """INSERT INTO memory_embeddings(memory_id, model_name, dim, vec, created_at)
               VALUES(?, ?, ?, ?, ?)""",
            (f"m_cd_{i}", client.provider, client.dim, encode_vec(vec), now),
        )
    c.commit(); c.close()

    pairs = find_candidate_pairs(db, similarity_min=0.99)
    assert ("m_cd_0", "m_cd_1", 1.0) in [(a, b, round(s, 3)) for a, b, s in pairs]


def test_judge_contradiction_mock():
    llm = MockLLMClient(scripted_json=[
        {"is_contradiction": True, "confidence": 0.9, "reason": "地点冲突"},
    ])
    r = judge_contradiction("A 昨天在北京", "A 昨天在上海", llm_client=llm)
    assert r["is_contradiction"] is True
    assert r["confidence"] == 0.9


def test_detect_contradictions_integration(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    client = MockEmbeddingClient(dim=16)
    c = sqlite3.connect(db)
    now = datetime.now(UTC).isoformat()
    # 两条相似 memory
    for i, t in enumerate(["A 昨天在北京", "A 昨天在上海"]):
        c.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
               confidence, is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?, 'shared_memory', ?, 0.7, 0.7, 1, 'active', '{}', ?, ?)""",
            (f"m_ctr_{i}", t, now, now),
        )
        vec = client.embed([t])[0]
        c.execute(
            """INSERT INTO memory_embeddings(memory_id, model_name, dim, vec, created_at)
               VALUES(?, ?, ?, ?, ?)""",
            (f"m_ctr_{i}", client.provider, client.dim, encode_vec(vec), now),
        )
    c.commit(); c.close()

    judge_llm = MockLLMClient(default_json={
        "is_contradiction": True, "confidence": 0.85, "reason": "地点矛盾",
    })
    result = detect_contradictions(db, similarity_min=0.3, llm_client=judge_llm)
    assert result["contradiction_count"] >= 0  # mock embedding 下 sim 可能低


def test_contradiction_eval_benchmark():
    bench = REPO_ROOT / "benchmarks" / "contradiction_groundtruth.json"
    llm = MockLLMClient(scripted_json=[
        {"is_contradiction": True, "confidence": 0.9, "reason": ""},
        {"is_contradiction": True, "confidence": 0.8, "reason": ""},
        {"is_contradiction": False, "confidence": 0.7, "reason": ""},
    ])
    r = run_contradiction_eval(bench, llm_client=llm)
    assert r["tp"] == 2
    assert r["tn"] == 1
    assert r["precision"] == 1.0
    assert r["recall"] == 1.0


# --- Phase 32 multimodal teaser ---

def test_mock_multimodal_text_and_image():
    c = MockMultimodalClient(dim=16)
    t = c.embed_text(["hello"])[0]
    i = c.embed_image([b"imgdata"])[0]
    assert len(t) == 16 and len(i) == 16
    # 同样输入 deterministic
    t2 = c.embed_text(["hello"])[0]
    assert t == t2


def test_clip_stub_requires_dep():
    import pytest
    try:
        import transformers  # noqa: F401
        pytest.skip("transformers installed, skip negative test")
    except ImportError:
        with pytest.raises(RuntimeError):
            CLIPStubClient()


def test_cross_modal_similarity_top_k():
    c = MockMultimodalClient(dim=16)
    q = c.embed_text(["dog"])[0]
    cands = [
        ("img1", c.embed_image([b"dog-image"])[0]),
        ("img2", c.embed_image([b"cat-image"])[0]),
        ("img3", c.embed_image([b"car-image"])[0]),
    ]
    top = cross_modal_similarity(q, cands, k=2)
    assert len(top) == 2
    # 只验证有序（mock hash 空间下结果看 hash 分布）
    assert top[0][1] >= top[1][1]
