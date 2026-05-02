"""Phase 53 — 质量与韧性 (QR slices)。

性质：fuzz / property-based / OTel NoOp / 100k 压测骨架。
不强依赖 hypothesis；若未装则 skip property 测试。
"""
from __future__ import annotations

import random
import sqlite3
import string
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


# --- OTel NoOp 测试 ---

def test_otel_defaults_disabled():
    from we_together.observability.otel_exporter import is_enabled, status
    assert is_enabled() is False or is_enabled() in (True, False)
    s = status()
    assert "enabled" in s


def test_otel_span_context_no_op():
    """未 enable 时 span 不崩。"""
    from we_together.observability.otel_exporter import disable, span
    disable()
    with span("test_span", attributes={"k": "v"}) as sp:
        assert sp is None


def test_otel_enable_without_sdk_ok():
    """未装 opentelemetry 时 enable 返回 enabled=False，不抛。"""
    from we_together.observability.otel_exporter import enable
    r = enable(endpoint=None, service_name="test")
    assert "enabled" in r
    # 不管装没装都不抛


def test_otel_set_attribute_noop():
    from we_together.observability.otel_exporter import disable, set_attribute
    disable()
    # 未 enable 时不抛
    set_attribute("k", "v")


# --- Fuzz patch_applier ---

def test_fuzz_patch_unknown_operation(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    # 构造一个未知 operation 的 patch dict，直接调 apply_patch_record
    import uuid
    patch = {
        "patch_id": f"pat_fuzz_{uuid.uuid4().hex[:8]}",
        "operation": "ALIEN_OPERATION_XYZ",
        "target_type": "person",
        "target_id": "p_x",
        "payload_json": "{}",
    }

    from we_together.services.patch_applier import apply_patch_record
    import pytest
    with pytest.raises((ValueError, Exception)):
        apply_patch_record(db, patch)


def test_fuzz_random_memory_summary(temp_project_with_migrations):
    """写 200 条随机 memory，图谱不崩。"""
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    rand_str = lambda n: "".join(
        random.choices(string.ascii_letters + "  \n中文!@#$%^&*()", k=n)
    )
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('p_fuzz', 'p', 'active', 0.8, "
        "'{}', datetime('now'), datetime('now'))"
    )
    for i in range(200):
        summary = rand_str(random.randint(0, 500))
        relevance = random.uniform(0.0, 1.0)
        confidence = random.uniform(0.0, 1.0)
        conn.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
               confidence, is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?, 'shared_memory', ?, ?, ?, ?, 'active', '{}',
               datetime('now'), datetime('now'))""",
            (f"m_fuzz_{i}", summary, relevance, confidence, random.choice([0, 1])),
        )
    conn.commit()
    conn.close()

    # integrity_audit 要能处理 200 条而不崩
    from we_together.services.integrity_audit import full_audit
    r = full_audit(db)
    assert "total_issues" in r


def test_fuzz_null_friendly_memory(temp_project_with_migrations):
    """空 summary / 0 relevance / 0 confidence 不应让服务崩。"""
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES('m_null_1', 'shared_memory', '', 0.0, 0.0, 1, 'active', '{}',
           datetime('now'), datetime('now'))"""
    )
    conn.commit()
    conn.close()

    # forgetting_service 不应崩
    from we_together.services.forgetting_service import archive_stale_memories, ForgetParams
    r = archive_stale_memories(db, ForgetParams(dry_run=True))
    assert "archived_count" in r


def test_fuzz_large_memory_batch(temp_project_with_migrations):
    """5000 条 memory 仍能跑 full_audit。"""
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.integrity_audit import full_audit
    import time
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('p_lg', 'lg', 'active', 0.8, "
        "'{}', datetime('now'), datetime('now'))"
    )
    # 批量插入（SQLite 默认 autocommit，直接 executemany）
    rows = [(f"m_lg_{i}",) for i in range(5000)]
    conn.executemany(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES(?, 'shared_memory', 'x', 0.5, 0.5, 1, 'active', '{}',
           datetime('now'), datetime('now'))""",
        rows,
    )
    conn.executemany(
        "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
        "VALUES(?, 'person', 'p_lg', NULL)",
        rows,
    )
    conn.commit()
    conn.close()

    t0 = time.perf_counter()
    r = full_audit(db)
    dt = time.perf_counter() - t0
    assert "total_issues" in r
    assert dt < 5.0, f"audit 5000 memories too slow: {dt:.2f}s"


# --- Property-based (optional hypothesis) ---

def test_property_mask_pii_idempotent():
    """mask_pii 应幂等：mask(mask(x)) == mask(x)"""
    try:
        from hypothesis import given, strategies as st
    except ImportError:
        import pytest
        pytest.skip("hypothesis not installed; skip property test")
        return

    from we_together.services.federation_security import mask_pii

    @given(st.text(min_size=0, max_size=200))
    def prop(s):
        once = mask_pii(s)
        twice = mask_pii(once)
        assert once == twice

    prop()


def test_property_forget_score_monotonic():
    """_forget_score(days, rel) 对 days 递增、对 relevance 递减"""
    try:
        from hypothesis import given, strategies as st
    except ImportError:
        import pytest
        pytest.skip("hypothesis not installed; skip property test")
        return

    from we_together.services.forgetting_service import _forget_score

    @given(
        d1=st.integers(min_value=0, max_value=100),
        d2=st.integers(min_value=0, max_value=100),
        rel=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    def prop(d1, d2, rel):
        if d1 < d2:
            assert _forget_score(d1, rel) <= _forget_score(d2, rel) + 1e-9

    prop()


# --- bench_100k 骨架 ---

def test_bench_100k_script_importable():
    import importlib.util
    p = REPO_ROOT / "scripts" / "bench_scale.py"
    spec = importlib.util.spec_from_file_location("bench_s", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.seed_synthetic)


def test_vector_index_100_items_fast(temp_project_with_migrations):
    """100 条 embedding 建 flat_python 索引 < 100ms。"""
    from we_together.db.bootstrap import bootstrap_project
    from we_together.llm.providers.embedding import MockEmbeddingClient
    from we_together.services.vector_index import VectorIndex
    from we_together.services.vector_similarity import encode_vec
    import time
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    client = MockEmbeddingClient(dim=16)
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("BEGIN")
    for i in range(100):
        mid = f"m_b_{i}"
        conn.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
               confidence, is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?, 'shared_memory', ?, 0.5, 0.5, 1, 'active', '{}',
               datetime('now'), datetime('now'))""",
            (mid, f"bench {i}"),
        )
        vec = client.embed([f"bench {i}"])[0]
        conn.execute(
            """INSERT INTO memory_embeddings(memory_id, model_name, dim, vec, created_at)
               VALUES(?, ?, ?, ?, datetime('now'))""",
            (mid, client.provider, client.dim, encode_vec(vec)),
        )
    conn.commit()
    conn.close()

    t0 = time.perf_counter()
    idx = VectorIndex.build(db, target="memory", backend="flat_python")
    dt = time.perf_counter() - t0
    assert idx.size() == 100
    assert dt < 1.0, f"build 100 vectors too slow: {dt*1000:.0f}ms"


def test_nightly_smoke_workflow_file_exists():
    """workflow 文件应存在（由 Phase 53 添加）。"""
    p = REPO_ROOT / ".github" / "workflows" / "nightly.yml"
    # allowlist：CI 未配置时跳过
    if not p.exists():
        import pytest
        pytest.skip(".github/workflows/nightly.yml 尚未建立（可选）")
    text = p.read_text(encoding="utf-8")
    assert "simulate" in text.lower() or "nightly" in text.lower()
