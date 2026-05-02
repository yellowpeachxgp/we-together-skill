from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script_module(script_name: str, module_name: str):
    script_path = REPO_ROOT / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _touch_tenant_db(root: Path, tenant_id: str) -> Path:
    db_path = root / "tenants" / tenant_id / "db" / "main.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.touch()
    return db_path


def test_import_image_cli_routes_to_tenant_db_root(tmp_path, monkeypatch):
    module = _load_script_module("import_image.py", "import_image_phase_70_parallel")
    tenant_db = _touch_tenant_db(tmp_path / "proj", "alpha")
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fake-image")

    captured: dict[str, object] = {}

    def fake_ocr_to_memory(
        db_path: Path,
        *,
        image_bytes: bytes,
        owner_id: str,
        scene_id: str | None = None,
        visibility: str = "shared",
        vision_client,
    ) -> dict:
        captured["db_path"] = db_path
        captured["image_bytes"] = image_bytes
        captured["owner_id"] = owner_id
        captured["scene_id"] = scene_id
        captured["visibility"] = visibility
        captured["vision_provider"] = getattr(vision_client, "provider", None)
        return {"media_id": "media_1", "memory_id": "memory_1"}

    monkeypatch.setattr(module, "ocr_to_memory", fake_ocr_to_memory)
    monkeypatch.setattr(
        "sys.argv",
        [
            "import_image.py",
            "--root",
            str(tmp_path / "proj"),
            "--tenant-id",
            "alpha",
            "--image",
            str(image_path),
            "--owner",
            "person_alice",
            "--scene",
            "scene_1",
            "--visibility",
            "group",
        ],
    )

    assert module.main() == 0
    assert captured["db_path"] == tenant_db
    assert captured["image_bytes"] == b"fake-image"
    assert captured["owner_id"] == "person_alice"
    assert captured["scene_id"] == "scene_1"
    assert captured["visibility"] == "group"
    assert captured["vision_provider"] == "mock_vision"


def test_import_llm_cli_routes_to_tenant_db_root(tmp_path, monkeypatch):
    module = _load_script_module("import_llm.py", "import_llm_phase_70_parallel")
    tenant_db = _touch_tenant_db(tmp_path / "proj", "alpha")

    captured: dict[str, object] = {}

    def fake_get_llm_client(provider: str | None = None):
        captured["provider"] = provider
        return object()

    def fake_extract_candidates_from_text(
        *,
        db_path: Path,
        text: str,
        source_name: str,
        llm_client,
    ) -> dict:
        captured["db_path"] = db_path
        captured["text"] = text
        captured["source_name"] = source_name
        captured["llm_client"] = llm_client
        return {
            "job_id": "job_1",
            "evidence_id": "evd_1",
            "identity_candidates": 1,
            "relation_clues": 0,
            "event_candidates": 0,
        }

    monkeypatch.setattr(module, "get_llm_client", fake_get_llm_client)
    monkeypatch.setattr(module, "extract_candidates_from_text", fake_extract_candidates_from_text)
    monkeypatch.setattr(
        "sys.argv",
        [
            "import_llm.py",
            "--root",
            str(tmp_path / "proj"),
            "--tenant-id",
            "alpha",
            "--text",
            "Alice and Bob are friends",
            "--source-name",
            "manual",
            "--provider",
            "mock",
        ],
    )

    assert module.main() == 0
    assert captured["provider"] == "mock"
    assert captured["db_path"] == tenant_db
    assert captured["text"] == "Alice and Bob are friends"
    assert captured["source_name"] == "manual"


def test_import_wechat_cli_routes_to_tenant_db_root(tmp_path, monkeypatch):
    module = _load_script_module("import_wechat.py", "import_wechat_phase_70_parallel")
    tenant_db = _touch_tenant_db(tmp_path / "proj", "alpha")
    csv_path = tmp_path / "wechat.csv"
    csv_path.write_text(
        "time,sender,content\n"
        "2026-04-22 08:00:00,Alice,hi\n",
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    def fake_import_wechat_text(*, db_path: Path, csv_path: Path, chat_name: str | None = None) -> dict:
        captured["db_path"] = db_path
        captured["csv_path"] = csv_path
        captured["chat_name"] = chat_name
        return {
            "job_id": "job_wx_1",
            "messages": 1,
            "senders": 1,
            "relation_clues": 0,
            "group_clue_id": None,
        }

    monkeypatch.setattr(module, "import_wechat_text", fake_import_wechat_text)
    monkeypatch.setattr(
        "sys.argv",
        [
            "import_wechat.py",
            "--root",
            str(tmp_path / "proj"),
            "--tenant-id",
            "alpha",
            "--file",
            str(csv_path),
            "--chat-name",
            "Alpha Group",
        ],
    )

    assert module.main() == 0
    assert captured["db_path"] == tenant_db
    assert captured["csv_path"] == csv_path
    assert captured["chat_name"] == "Alpha Group"
