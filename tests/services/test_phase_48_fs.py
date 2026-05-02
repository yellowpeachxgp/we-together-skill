"""Phase 48 — 联邦安全 + PII (FS slices)。"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load_server():
    p = REPO_ROOT / "scripts" / "federation_http_server.py"
    spec = importlib.util.spec_from_file_location("fed_48", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_generate_and_hash_token():
    from we_together.services.federation_security import generate_token, hash_token
    t = generate_token()
    assert isinstance(t, str) and len(t) > 20
    h = hash_token(t)
    assert len(h) == 64  # sha256 hex


def test_verify_token():
    from we_together.services.federation_security import (
        generate_token, hash_token, verify_token,
    )
    t = generate_token()
    h = hash_token(t)
    assert verify_token(t, [h])
    assert not verify_token("wrong", [h])


def test_rate_limiter_allows_up_to_limit():
    from we_together.services.federation_security import RateLimiter
    rl = RateLimiter(max_per_minute=5, window_seconds=60)
    for _ in range(5):
        assert rl.allow("user1") is True
    assert rl.allow("user1") is False
    # 其他 user 独立
    assert rl.allow("user2") is True


def test_mask_email():
    from we_together.services.federation_security import mask_email
    s = "联系 alice@example.com 即可"
    masked = mask_email(s)
    assert "alice@" not in masked
    assert "@example.com" in masked
    assert "***" in masked


def test_mask_phone():
    from we_together.services.federation_security import mask_phone
    assert "***" in mask_phone("call 13812345678")
    assert "5678" in mask_phone("call 13812345678")


def test_mask_pii_combined():
    from we_together.services.federation_security import mask_pii
    s = "contact a@b.co or 13812345678"
    r = mask_pii(s)
    assert "a@b.co" not in r
    assert "13812345678" not in r


def test_sanitize_record_masks_fields():
    from we_together.services.federation_security import sanitize_record
    r = sanitize_record({
        "person_id": "p1",
        "primary_name": "Alice (alice@work.com)",
        "summary": "contact 13800000000",
        "other": "untouched",
    })
    assert "alice@" not in r["primary_name"]
    assert "13800000000" not in r["summary"]
    assert r["other"] == "untouched"
    assert r["person_id"] == "p1"


def test_is_exportable_private_blocked():
    from we_together.services.federation_security import is_exportable
    assert is_exportable({"visibility": "private"}) is False
    assert is_exportable({"visibility_level": "private"}) is False
    assert is_exportable({"metadata": {"exportable": False}}) is False
    assert is_exportable({"visibility": "shared"}) is True
    assert is_exportable({"metadata": {"exportable": True}}) is True
    assert is_exportable({}) is True  # 默认可导出


def test_server_requires_auth_when_tokens_set(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.federation_client import FederationClient
    from we_together.services.federation_security import generate_token, hash_token
    from http.server import HTTPServer

    bootstrap_project(temp_project_with_migrations)
    m = _load_server()

    token = generate_token()
    handler = m.make_handler(
        temp_project_with_migrations,
        allowed_token_hashes=[hash_token(token)],
        rate_limiter=None,
        mask_pii_on_export=False,
    )
    server = HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thr = threading.Thread(target=server.serve_forever, daemon=True)
    thr.start()

    try:
        # 无 token → 401
        c = FederationClient(f"http://127.0.0.1:{port}")
        import pytest
        with pytest.raises(RuntimeError, match="401"):
            c.list_persons()

        # 有 token → 200
        c2 = FederationClient(f"http://127.0.0.1:{port}", bearer_token=token)
        r = c2.list_persons()
        assert "persons" in r
    finally:
        server.shutdown()
        server.server_close()


def test_server_rate_limits(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.federation_client import FederationClient
    from we_together.services.federation_security import RateLimiter
    from http.server import HTTPServer

    bootstrap_project(temp_project_with_migrations)
    m = _load_server()

    limiter = RateLimiter(max_per_minute=3, window_seconds=60)
    handler = m.make_handler(
        temp_project_with_migrations,
        allowed_token_hashes=[],  # 无鉴权 → key='anonymous'
        rate_limiter=limiter,
        mask_pii_on_export=False,
    )
    server = HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thr = threading.Thread(target=server.serve_forever, daemon=True)
    thr.start()

    try:
        c = FederationClient(f"http://127.0.0.1:{port}")
        # capabilities 不经 rate limit（在 auth 前）
        for _ in range(5):
            c.capabilities()
        # list_persons 经 rate limit
        c.list_persons()
        c.list_persons()
        c.list_persons()
        import pytest
        with pytest.raises(RuntimeError, match="429"):
            c.list_persons()
    finally:
        server.shutdown()
        server.server_close()


def test_server_masks_pii_in_response(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.federation_client import FederationClient
    from http.server import HTTPServer

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('p_pii','Alice (alice@corp.com)',"
        "'active',0.8,'{}', datetime('now'),datetime('now'))"
    )
    conn.commit()
    conn.close()

    m = _load_server()
    handler = m.make_handler(
        temp_project_with_migrations,
        allowed_token_hashes=[],
        rate_limiter=None,
        mask_pii_on_export=True,
    )
    server = HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thr = threading.Thread(target=server.serve_forever, daemon=True)
    thr.start()

    try:
        c = FederationClient(f"http://127.0.0.1:{port}")
        r = c.list_persons()
        for p in r["persons"]:
            if p["person_id"] == "p_pii":
                assert "alice@corp.com" not in p["primary_name"]
                assert "@corp.com" in p["primary_name"]
    finally:
        server.shutdown()
        server.server_close()


def test_capabilities_declares_v1_1():
    m = _load_server()
    cap = m._capabilities()
    assert cap["federation_protocol_version"] == "1.1"
    assert cap["pii_masking"] is True
    assert cap["rate_limit_per_minute"] == 60
    assert cap["auth"].startswith("bearer")
