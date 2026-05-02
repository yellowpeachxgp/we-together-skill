import json
from pathlib import Path

from we_together.db.bootstrap import bootstrap_project
from we_together.services.federation_fetcher import (
    FederationFetcher,
    HTTPBackend,
    LocalFileBackend,
    build_default_fetcher,
    inject_eager_into_participants,
)
from we_together.services.federation_service import register_external_person


def _write_remote_stub(root: Path, skill: str, pid: str, data: dict) -> None:
    fdir = root / "federation" / skill
    fdir.mkdir(parents=True, exist_ok=True)
    (fdir / f"{pid}.json").write_text(json.dumps(data, ensure_ascii=False))


# --- LocalFileBackend ---

def test_local_file_backend_reads_stub(tmp_path):
    _write_remote_stub(tmp_path, "partner", "ext_alice",
                        {"display_name": "远端 Alice", "persona_summary": "项目经理"})
    b = LocalFileBackend(tmp_path)
    data = b.fetch_remote_person("partner", "ext_alice")
    assert data is not None
    assert data["display_name"] == "远端 Alice"


def test_local_file_backend_missing(tmp_path):
    b = LocalFileBackend(tmp_path)
    assert b.fetch_remote_person("nope", "x") is None


# --- Fetcher + cache ---

def test_fetcher_caches(tmp_path):
    _write_remote_stub(tmp_path, "s1", "p1", {"display_name": "A"})
    f = FederationFetcher(backend=LocalFileBackend(tmp_path))
    first = f.get_remote_person("s1", "p1")
    second = f.get_remote_person("s1", "p1")
    assert first == second
    # 第二次命中内存 cache（内部计数）
    assert ("s1", "p1") in f._cache


def test_fetcher_cache_ttl_expires(tmp_path):
    import time as _t
    _write_remote_stub(tmp_path, "s2", "p2", {"display_name": "B"})
    f = FederationFetcher(backend=LocalFileBackend(tmp_path), cache_ttl_seconds=0)
    f.get_remote_person("s2", "p2")
    # ttl=0 → 下次应该重新 backend.fetch
    _t.sleep(0.01)
    assert f.get_remote_person("s2", "p2") is not None


def test_fetcher_invalidate_cache(tmp_path):
    _write_remote_stub(tmp_path, "s3", "p3", {"x": 1})
    f = build_default_fetcher(tmp_path)
    f.get_remote_person("s3", "p3")
    n = f.invalidate_cache()
    assert n == 1


# --- eager refs 链 ---

def test_fetch_eager_refs_returns_only_eager(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    register_external_person(db, external_skill_name="partner",
                              external_person_id="pid_eager",
                              display_name="Eager", policy="eager")
    register_external_person(db, external_skill_name="partner",
                              external_person_id="pid_lazy",
                              display_name="Lazy", policy="lazy")
    _write_remote_stub(tmp_path, "partner", "pid_eager",
                        {"display_name": "E", "persona_summary": "X"})
    f = build_default_fetcher(tmp_path)

    results = f.fetch_eager_refs(db)
    assert len(results) == 1
    assert results[0]["fetched"] is True
    assert results[0]["ref"]["display_name"] == "Eager"


def test_fetch_eager_refs_handles_missing_remote(
    temp_project_with_migrations, tmp_path,
):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    register_external_person(db, external_skill_name="x",
                              external_person_id="missing", policy="eager")
    f = build_default_fetcher(tmp_path)
    results = f.fetch_eager_refs(db)
    assert len(results) == 1
    assert results[0]["fetched"] is False
    assert results[0]["remote_data"] is None


def test_inject_eager_into_participants():
    pkg = {"participants": [{"person_id": "local_1"}]}
    fetched = [
        {"ref": {"external_skill_name": "s", "external_person_id": "e1",
                 "display_name": "Local Alias", "trust_level": 0.7},
         "remote_data": {"display_name": "Remote A", "persona_summary": "PM"},
         "fetched": True},
    ]
    new_pkg = inject_eager_into_participants(pkg, fetched)
    assert len(new_pkg["participants"]) == 2
    assert new_pkg["participants"][1]["remote"] is True
    assert new_pkg["federation"]["remote_participants"] == 1


def test_inject_skips_unfetched():
    pkg = {"participants": []}
    fetched = [{"ref": {"external_skill_name": "s", "external_person_id": "e"},
                 "remote_data": None, "fetched": False}]
    new_pkg = inject_eager_into_participants(pkg, fetched)
    assert new_pkg["participants"] == []


# --- HTTPBackend stub ---

def test_http_backend_construct():
    b = HTTPBackend(base_url="https://example.com/api", token="tok")
    assert b.name == "http"
    assert b.base_url == "https://example.com/api"
