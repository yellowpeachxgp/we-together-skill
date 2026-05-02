import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from embed_backfill import backfill_embeddings  # noqa: E402

from we_together.db.bootstrap import bootstrap_project  # noqa: E402
from we_together.eval.embedding_retrieval_eval import (  # noqa: E402
    run_embedding_retrieval_eval,
)
from we_together.llm.providers.embedding import MockEmbeddingClient  # noqa: E402
from we_together.services.embedding_recall import associate_by_embedding  # noqa: E402
from we_together.services.vector_similarity import (  # noqa: E402
    cosine_similarity,
    decode_vec,
    encode_vec,
    top_k,
)

# --- vector_similarity ---

def test_encode_decode_roundtrip():
    vec = [0.1, -0.2, 0.3, 0.4]
    decoded = decode_vec(encode_vec(vec))
    # float32 精度损失，容差比较
    for a, b in zip(vec, decoded, strict=False):
        assert abs(a - b) < 1e-5


def test_cosine_identical():
    v = [1.0, 2.0, 3.0]
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-6


def test_cosine_orthogonal():
    assert abs(cosine_similarity([1, 0], [0, 1])) < 1e-6


def test_cosine_empty():
    assert cosine_similarity([], [1, 2]) == 0.0


def test_top_k_order():
    q = [1.0, 0.0]
    candidates = [
        ("a", [1.0, 0.1]),
        ("b", [0.0, 1.0]),
        ("c", [0.9, 0.2]),
    ]
    result = top_k(q, candidates, k=2)
    assert result[0][0] in ("a", "c")


# --- MockEmbeddingClient ---

def test_mock_embedding_deterministic():
    c = MockEmbeddingClient(dim=16)
    v1 = c.embed(["hello world"])[0]
    v2 = c.embed(["hello world"])[0]
    assert v1 == v2
    assert len(v1) == 16


def test_mock_embedding_different_inputs():
    c = MockEmbeddingClient(dim=8)
    v1 = c.embed(["apple"])[0]
    v2 = c.embed(["banana"])[0]
    assert v1 != v2


# --- backfill + recall ---

def test_backfill_memory_embeddings(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    c = sqlite3.connect(db)
    for i, s in enumerate(["工作会议", "家庭聚餐", "周末爬山"]):
        c.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
               confidence, is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?, 'shared_memory', ?, 0.7, 0.7, 1, 'active', '{}',
               datetime('now'), datetime('now'))""",
            (f"m_be_{i}", s),
        )
    c.commit()
    c.close()

    client = MockEmbeddingClient(dim=16)
    result = backfill_embeddings(db, target="memory", embedding_client=client)
    assert result["inserted"] == 3
    assert result["dim"] == 16


def test_associate_by_embedding_finds_similar(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    client = MockEmbeddingClient(dim=16)
    # 手工写 3 条 + embed
    c = sqlite3.connect(db)
    texts = {"m_a": "工作会议 项目 代码", "m_b": "周末 爬山", "m_c": "code review"}
    for mid, t in texts.items():
        c.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
               confidence, is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?, 'shared_memory', ?, 0.7, 0.7, 1, 'active', '{}',
               datetime('now'), datetime('now'))""",
            (mid, t),
        )
    c.commit()
    c.close()

    backfill_embeddings(db, target="memory", embedding_client=client)
    result = associate_by_embedding(
        db, seed_text="工作会议 项目 代码",
        embedding_client=client, top_k=2,
    )
    assert result["candidate_count"] == 3
    assert result["associated"][0] == "m_a"  # 完全相同 → 第一


def test_associate_no_embeddings(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    client = MockEmbeddingClient(dim=8)
    result = associate_by_embedding(
        db, seed_text="x", embedding_client=client,
    )
    assert result["reason"] == "no_embeddings_indexed"


def test_associate_by_embedding_accepts_index_backend(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    client = MockEmbeddingClient(dim=16)
    c = sqlite3.connect(db)
    c.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES('m_idx_backend', 'shared_memory', '工作会议 项目 代码', 0.7, 0.7, 1, 'active', '{}',
           datetime('now'), datetime('now'))"""
    )
    c.commit()
    c.close()
    backfill_embeddings(db, target="memory", embedding_client=client)

    result = associate_by_embedding(
        db,
        seed_text="工作会议 项目 代码",
        embedding_client=client,
        top_k=1,
        index_backend="flat_python",
    )
    assert result["associated"] == ["m_idx_backend"]


# --- eval ---

def test_embedding_retrieval_eval(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    client = MockEmbeddingClient(dim=16)
    bench = REPO_ROOT / "benchmarks" / "embedding_retrieval_groundtruth.json"
    result = run_embedding_retrieval_eval(db, bench, embedding_client=client)
    assert result["total"] == 2
    # mock embedding 是 hash-based，期望值与 query 完全相同才 pass
    # 至少保证 eval 不炸
    assert "pass_rate" in result
    assert "queries" in result
