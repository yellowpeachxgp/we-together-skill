from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "webui_host.py"


def load_webui_host():
    spec = importlib.util.spec_from_file_location("wt_webui_host", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_webui_host_script_importable():
    module = load_webui_host()
    assert hasattr(module, "build_runtime_status")
    assert hasattr(module, "run_local_chat_turn")


def test_runtime_status_uses_local_skill_mode(tmp_path):
    module = load_webui_host()
    status = module.build_runtime_status(
        root=tmp_path,
        tenant_id=None,
        provider=None,
        adapter="claude",
    )
    assert status["mode"] == "local_skill"
    assert status["provider"] == "mock"
    assert status["adapter"] == "claude"
    assert status["token_required"] is False


def create_minimal_runtime_db(root: Path) -> None:
    db_dir = root / "db"
    db_dir.mkdir(parents=True)
    conn = sqlite3.connect(db_dir / "main.sqlite3")
    try:
        conn.executescript(
            """
            CREATE TABLE scenes(
              scene_id TEXT PRIMARY KEY,
              scene_type TEXT NOT NULL,
              group_id TEXT,
              trigger_event_id TEXT,
              scene_summary TEXT,
              location_scope TEXT,
              channel_scope TEXT,
              visibility_scope TEXT,
              time_scope TEXT,
              role_scope TEXT,
              access_scope TEXT,
              privacy_scope TEXT,
              activation_barrier TEXT,
              environment_json TEXT,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE persons(
              person_id TEXT PRIMARY KEY,
              primary_name TEXT,
              status TEXT NOT NULL,
              persona_summary TEXT,
              confidence REAL,
              metadata_json TEXT
            );
            CREATE TABLE relations(
              relation_id TEXT PRIMARY KEY,
              core_type TEXT,
              custom_label TEXT,
              summary TEXT,
              status TEXT NOT NULL,
              confidence REAL
            );
            CREATE TABLE groups(
              group_id TEXT PRIMARY KEY,
              group_type TEXT,
              name TEXT,
              summary TEXT,
              status TEXT NOT NULL
            );
            CREATE TABLE memories(
              memory_id TEXT PRIMARY KEY,
              memory_type TEXT,
              summary TEXT,
              status TEXT NOT NULL,
              confidence REAL,
              metadata_json TEXT
            );
            CREATE TABLE states(
              state_id TEXT PRIMARY KEY,
              scope_type TEXT,
              scope_id TEXT,
              state_type TEXT,
              value_json TEXT,
              confidence REAL
            );
            CREATE TABLE scene_participants(
              scene_id TEXT NOT NULL,
              person_id TEXT NOT NULL,
              activation_score REAL,
              activation_state TEXT,
              is_speaking INTEGER
            );
            CREATE TABLE group_members(
              group_id TEXT NOT NULL,
              person_id TEXT NOT NULL,
              role_label TEXT,
              status TEXT
            );
            CREATE TABLE memory_owners(
              memory_id TEXT NOT NULL,
              owner_type TEXT NOT NULL,
              owner_id TEXT NOT NULL,
              role_label TEXT
            );
            CREATE TABLE entity_links(
              from_type TEXT NOT NULL,
              from_id TEXT NOT NULL,
              relation_type TEXT NOT NULL,
              to_type TEXT NOT NULL,
              to_id TEXT NOT NULL,
              weight REAL,
              metadata_json TEXT
            );
            CREATE TABLE events(
              event_id TEXT PRIMARY KEY,
              event_type TEXT,
              source_type TEXT,
              scene_id TEXT,
              group_id TEXT,
              timestamp TEXT,
              summary TEXT,
              visibility_level TEXT,
              confidence REAL,
              metadata_json TEXT,
              created_at TEXT
            );
            CREATE TABLE patches(
              patch_id TEXT PRIMARY KEY,
              source_event_id TEXT,
              target_type TEXT,
              target_id TEXT,
              operation TEXT,
              payload_json TEXT,
              confidence REAL,
              reason TEXT,
              status TEXT,
              created_at TEXT,
              applied_at TEXT
            );
            CREATE TABLE snapshots(
              snapshot_id TEXT PRIMARY KEY,
              based_on_snapshot_id TEXT,
              trigger_event_id TEXT,
              summary TEXT,
              graph_hash TEXT,
              created_at TEXT
            );
            CREATE TABLE local_branches(
              branch_id TEXT PRIMARY KEY,
              scope_type TEXT,
              scope_id TEXT,
              status TEXT NOT NULL,
              reason TEXT,
              created_from_event_id TEXT,
              created_at TEXT,
              resolved_at TEXT
            );
            CREATE TABLE branch_candidates(
              candidate_id TEXT PRIMARY KEY,
              branch_id TEXT NOT NULL,
              label TEXT,
              payload_json TEXT,
              confidence REAL,
              status TEXT,
              created_at TEXT
            );
            CREATE TABLE objects(
              object_id TEXT PRIMARY KEY,
              kind TEXT,
              name TEXT,
              owner_type TEXT,
              owner_id TEXT,
              status TEXT,
              effective_from TEXT,
              effective_until TEXT
            );
            CREATE TABLE places(
              place_id TEXT PRIMARY KEY,
              name TEXT,
              scope TEXT,
              status TEXT,
              effective_from TEXT,
              effective_until TEXT
            );
            CREATE TABLE projects(
              project_id TEXT PRIMARY KEY,
              name TEXT,
              goal TEXT,
              status TEXT,
              priority TEXT,
              started_at TEXT,
              due_at TEXT
            );
            CREATE TABLE agent_drives(
              drive_id TEXT PRIMARY KEY,
              person_id TEXT NOT NULL,
              drive_type TEXT NOT NULL,
              intensity REAL NOT NULL,
              source_memory_ids_json TEXT,
              source_event_ids_json TEXT,
              status TEXT,
              satisfied_by_event_id TEXT,
              activated_at TEXT,
              satisfied_at TEXT,
              metadata_json TEXT
            );
            CREATE TABLE autonomous_actions(
              action_id INTEGER PRIMARY KEY AUTOINCREMENT,
              person_id TEXT NOT NULL,
              action_type TEXT NOT NULL,
              triggered_by_drive_id TEXT,
              triggered_by_memory_id TEXT,
              triggered_by_trace_id INTEGER,
              output_event_id TEXT,
              rationale TEXT,
              created_at TEXT
            );
            """
        )
        conn.execute(
            "INSERT INTO scenes(scene_id, scene_type, scene_summary, status, created_at, updated_at) "
            "VALUES ('scene_real', 'work_discussion', '真实本地场景', 'active', '2026-04-29T00:00:00Z', '2026-04-29T00:00:00Z')"
        )
        conn.execute(
            "INSERT INTO scenes(scene_id, scene_type, scene_summary, status, created_at, updated_at) "
            "VALUES ('scene_closed', 'private_chat', '已关闭场景', 'closed', '2026-04-29T00:00:00Z', '2026-04-29T00:00:00Z')"
        )
        conn.executemany(
            "INSERT INTO persons(person_id, primary_name, status, persona_summary, confidence, metadata_json) "
            "VALUES (?, ?, ?, ?, ?, '{}')",
            [
                ("p1", "Alice", "active", "理性领导者", 0.9),
                ("p2", "Bob", "active", "协调者", 0.8),
                ("p3", "Merged", "merged", None, 0.2),
            ],
        )
        conn.execute(
            "INSERT INTO relations(relation_id, core_type, custom_label, summary, status, confidence) "
            "VALUES ('r1', 'work', 'alice_bob', 'Alice and Bob work together', 'active', 0.8)"
        )
        conn.execute(
            "INSERT INTO groups(group_id, group_type, name, summary, status) "
            "VALUES ('g1', 'team', 'CoreEng', '核心工程组', 'active')"
        )
        conn.execute(
            "INSERT INTO memories(memory_id, memory_type, summary, status, confidence, metadata_json) "
            "VALUES ('m1', 'shared_memory', '一起完成项目复盘', 'active', 0.7, '{}')"
        )
        conn.execute(
            "INSERT INTO states(state_id, scope_type, scope_id, state_type, value_json, confidence) "
            "VALUES ('s1', 'person', 'p1', 'mood', '{\"mood\":\"focused\"}', 0.6)"
        )
        conn.executemany(
            "INSERT INTO scene_participants(scene_id, person_id, activation_score, activation_state, is_speaking) "
            "VALUES ('scene_real', ?, ?, ?, ?)",
            [("p1", 1.0, "explicit", 1), ("p2", 0.8, "latent", 0)],
        )
        conn.execute(
            "INSERT INTO group_members(group_id, person_id, role_label, status) "
            "VALUES ('g1', 'p1', 'owner', 'active')"
        )
        conn.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
            "VALUES ('m1', 'person', 'p1', 'shared')"
        )
        conn.execute(
            "INSERT INTO entity_links(from_type, from_id, relation_type, to_type, to_id, weight, metadata_json) "
            "VALUES ('relation', 'r1', 'supported_by_memory', 'memory', 'm1', 0.7, '{}')"
        )
        conn.execute(
            "INSERT INTO entity_links(from_type, from_id, relation_type, to_type, to_id, weight, metadata_json) "
            "VALUES ('person', 'p2', 'remembers', 'memory', 'm1', 0.6, '{}')"
        )
        conn.execute(
            "INSERT INTO events(event_id, event_type, source_type, scene_id, timestamp, summary, visibility_level, confidence, created_at) "
            "VALUES ('e1', 'dialogue_turn', 'webui', 'scene_real', '2026-04-29T00:01:00Z', 'Alice asked Bob for a review', 'visible', 0.9, '2026-04-29T00:01:00Z')"
        )
        conn.execute(
            "INSERT INTO patches(patch_id, source_event_id, target_type, target_id, operation, payload_json, confidence, reason, status, created_at, applied_at) "
            "VALUES ('patch1', 'e1', 'memory', 'm1', 'create_memory', '{\"memory_id\":\"m1\"}', 0.8, 'test patch', 'applied', '2026-04-29T00:02:00Z', '2026-04-29T00:02:00Z')"
        )
        conn.execute(
            "INSERT INTO snapshots(snapshot_id, trigger_event_id, summary, graph_hash, created_at) "
            "VALUES ('snap1', 'e1', 'after dialogue turn', 'hash1', '2026-04-29T00:03:00Z')"
        )
        conn.execute(
            "INSERT INTO local_branches(branch_id, scope_type, scope_id, status, reason, created_from_event_id, created_at) "
            "VALUES ('branch1', 'person', 'p1', 'open', 'operator review', 'e1', '2026-04-29T00:04:00Z')"
        )
        conn.execute(
            "INSERT INTO branch_candidates(candidate_id, branch_id, label, payload_json, confidence, status, created_at) "
            "VALUES ('cand_keep', 'branch1', '保留当前状态', '{\"effect_patches\":[]}', 0.4, 'open', '2026-04-29T00:04:00Z')"
        )
        conn.execute(
            "INSERT INTO branch_candidates(candidate_id, branch_id, label, payload_json, confidence, status, created_at) "
            "VALUES ('cand_apply', 'branch1', '应用复核修补', '{\"effect_patches\":[{\"operation\":\"update_entity\",\"target_type\":\"person\",\"target_id\":\"p1\",\"payload\":{\"summary\":\"reviewed\"}}]}', 0.7, 'open', '2026-04-29T00:04:00Z')"
        )
        conn.execute(
            "INSERT INTO objects(object_id, kind, name, owner_type, owner_id, status, effective_from) "
            "VALUES ('obj1', 'document', '复盘文档', 'person', 'p1', 'active', '2026-04-29T00:00:00Z')"
        )
        conn.execute(
            "INSERT INTO places(place_id, name, scope, status, effective_from) "
            "VALUES ('place1', '工作室', 'room', 'active', '2026-04-29T00:00:00Z')"
        )
        conn.execute(
            "INSERT INTO projects(project_id, name, goal, status, priority, started_at) "
            "VALUES ('proj1', 'Memory Mesh', 'ship cockpit', 'active', 'high', '2026-04-29T00:00:00Z')"
        )
        conn.execute(
            "INSERT INTO entity_links(from_type, from_id, relation_type, to_type, to_id, weight, metadata_json) "
            "VALUES ('project', 'proj1', 'involves', 'person', 'p1', 1.0, '{}')"
        )
        conn.execute(
            "INSERT INTO agent_drives(drive_id, person_id, drive_type, intensity, source_memory_ids_json, source_event_ids_json, status, activated_at, metadata_json) "
            "VALUES ('drive1', 'p1', 'curiosity', 0.8, '[\"m1\"]', '[\"e1\"]', 'active', '2026-04-29T00:05:00Z', '{}')"
        )
        conn.execute(
            "INSERT INTO autonomous_actions(person_id, action_type, triggered_by_drive_id, output_event_id, rationale, created_at) "
            "VALUES ('p1', 'reflect', 'drive1', 'e1', 'follow active curiosity drive', '2026-04-29T00:06:00Z')"
        )
        conn.commit()
    finally:
        conn.close()


def test_local_scenes_come_from_tenant_database(tmp_path):
    module = load_webui_host()
    create_minimal_runtime_db(tmp_path)

    result = module.list_local_scenes(root=tmp_path, tenant_id=None)

    assert result["source"] == "local_skill"
    assert result["scenes"] == [
        {
            "scene_id": "scene_real",
            "scene_type": "work_discussion",
            "scene_summary": "真实本地场景",
            "status": "active",
            "participant_count": 2,
        }
    ]


def test_local_summary_counts_current_database(tmp_path):
    module = load_webui_host()
    create_minimal_runtime_db(tmp_path)

    summary = module.build_local_summary(root=tmp_path, tenant_id=None)

    assert summary["source"] == "local_skill"
    assert summary["db_exists"] is True
    assert summary["person_count"] == 2
    assert summary["relation_count"] == 1
    assert summary["memory_count"] == 1
    assert summary["event_count"] == 1
    assert summary["patch_count"] == 1
    assert summary["snapshot_count"] == 1
    assert summary["open_local_branch_count"] == 1


def test_local_graph_exposes_real_runtime_nodes_and_edges(tmp_path):
    module = load_webui_host()
    create_minimal_runtime_db(tmp_path)

    graph = module.build_local_graph(root=tmp_path, tenant_id=None, scene_id="scene_real")

    node_ids = {node["id"] for node in graph["nodes"]}
    node_types = {node["type"] for node in graph["nodes"]}
    edge_types = {edge["type"] for edge in graph["edges"]}
    assert graph["source"] == "local_skill"
    assert {"p1", "p2", "r1", "m1", "g1", "scene_real", "s1", "obj1", "place1", "proj1"}.issubset(node_ids)
    assert {"person", "relation", "memory", "group", "scene", "state", "object", "place", "project"}.issubset(node_types)
    assert next(node for node in graph["nodes"] if node["id"] == "p1")["label"] == "Alice"
    assert next(node for node in graph["nodes"] if node["id"] == "m1")["label"] == "一起完成项目复盘"
    assert next(node for node in graph["nodes"] if node["id"] == "r1")["label"] == "alice_bob"
    assert {"scene_participant", "memory_owner", "group_member", "entity_link", "state_scope", "object_owner", "project_involves"}.issubset(edge_types)


def test_local_activity_lists_recent_events_patches_and_snapshots(tmp_path):
    module = load_webui_host()
    create_minimal_runtime_db(tmp_path)

    events = module.list_local_events(root=tmp_path, tenant_id=None, limit=5)
    patches = module.list_local_patches(root=tmp_path, tenant_id=None, limit=5)
    snapshots = module.list_local_snapshots(root=tmp_path, tenant_id=None, limit=5)

    assert events["events"][0]["event_id"] == "e1"
    assert events["events"][0]["summary"] == "Alice asked Bob for a review"
    assert patches["patches"][0]["patch_id"] == "patch1"
    assert patches["patches"][0]["payload_json"] == {"memory_id": "m1"}
    assert snapshots["snapshots"][0]["snapshot_id"] == "snap1"


def test_local_branches_include_decoded_candidates(tmp_path):
    module = load_webui_host()
    create_minimal_runtime_db(tmp_path)

    result = module.list_local_branches(root=tmp_path, tenant_id=None)

    assert result["source"] == "local_skill"
    assert result["branches"][0]["branch_id"] == "branch1"
    assert [candidate["candidate_id"] for candidate in result["branches"][0]["candidates"]] == [
        "cand_apply",
        "cand_keep",
    ]
    assert result["branches"][0]["candidates"][0]["payload_json"]["effect_patches"][0]["operation"] == "update_entity"


def test_local_world_lists_scene_aware_runtime_entities(tmp_path):
    module = load_webui_host()
    create_minimal_runtime_db(tmp_path)

    result = module.build_local_world(root=tmp_path, tenant_id=None, scene_id="scene_real")

    assert result["source"] == "local_skill"
    assert result["objects"][0]["object_id"] == "obj1"
    assert result["projects"][0]["project_id"] == "proj1"
    assert result["places"][0]["place_id"] == "place1"
    assert result["agent_drives"][0]["drive_id"] == "drive1"
    assert result["autonomous_actions"][0]["action_type"] == "reflect"


def test_local_world_tolerates_missing_runtime_tables(tmp_path):
    module = load_webui_host()
    create_minimal_runtime_db(tmp_path)
    conn = sqlite3.connect(tmp_path / "db" / "main.sqlite3")
    try:
        conn.execute("DROP TABLE objects")
        conn.execute("DROP TABLE places")
        conn.execute("DROP TABLE projects")
        conn.commit()
    finally:
        conn.close()

    result = module.build_local_world(root=tmp_path, tenant_id=None, scene_id="scene_real")

    assert result == {
        "source": "local_skill",
        "participants": ["p1", "p2"],
        "objects": [],
        "places": [],
        "projects": [],
        "agent_drives": [{"drive_id": "drive1", "person_id": "p1", "drive_type": "curiosity", "intensity": 0.8, "source_memory_ids_json": ["m1"], "source_event_ids_json": ["e1"], "status": "active", "satisfied_by_event_id": None, "activated_at": "2026-04-29T00:05:00Z", "satisfied_at": None, "metadata_json": {}}],
        "autonomous_actions": [{"action_id": 1, "person_id": "p1", "action_type": "reflect", "triggered_by_drive_id": "drive1", "triggered_by_memory_id": None, "triggered_by_trace_id": None, "output_event_id": "e1", "rationale": "follow active curiosity drive", "created_at": "2026-04-29T00:06:00Z"}],
    }


def test_bootstrap_seed_import_and_branch_resolution_use_local_runtime_services(monkeypatch, tmp_path):
    module = load_webui_host()
    create_minimal_runtime_db(tmp_path)
    calls = []

    def fake_bootstrap_project(root):
        calls.append(("bootstrap", root))

    def fake_seed_society_c(root):
        calls.append(("seed", root))
        return {"scenes": {"work": "scene_seeded"}}

    def fake_ingest_narration(db_path, text, source_name, scene_id=None):
        calls.append(("import", db_path, text, source_name, scene_id))
        return {"event_id": "evt_import", "snapshot_id": "snap_import", "person_ids": ["p1", "p2"]}

    def fake_apply_patch_record(db_path, patch):
        calls.append(("patch", db_path, patch))

    monkeypatch.setattr(module, "bootstrap_project", fake_bootstrap_project)
    monkeypatch.setattr(module, "seed_society_c", fake_seed_society_c)
    monkeypatch.setattr(module, "ingest_narration", fake_ingest_narration)
    monkeypatch.setattr(module, "apply_patch_record", fake_apply_patch_record)

    assert module.bootstrap_local_runtime(root=tmp_path, tenant_id=None)["db_path"].endswith("main.sqlite3")
    assert module.seed_local_demo(root=tmp_path, tenant_id=None)["seed"]["scenes"]["work"] == "scene_seeded"
    imported = module.import_local_narration(
        root=tmp_path,
        tenant_id=None,
        payload={"text": "小明和小红是朋友，最近一起做项目。", "source_name": "webui-test"},
    )
    resolved = module.resolve_local_branch(
        root=tmp_path,
        tenant_id=None,
        branch_id="branch1",
        payload={"candidate_id": "cand_apply", "reason": "operator approved"},
    )

    assert imported["result"]["event_id"] == "evt_import"
    assert resolved["branch_id"] == "branch1"
    assert resolved["selected_candidate_id"] == "cand_apply"
    assert calls[0] == ("bootstrap", tmp_path)
    assert calls[1] == ("bootstrap", tmp_path)
    assert calls[2] == ("seed", tmp_path)
    assert calls[3] == ("bootstrap", tmp_path)
    assert calls[4] == (
        "import",
        tmp_path / "db" / "main.sqlite3",
        "小明和小红是朋友，最近一起做项目。",
        "webui-test",
        None,
    )
    assert calls[5][0] == "patch"
    assert calls[5][2]["operation"] == "resolve_local_branch"
    assert calls[5][2]["payload_json"]["selected_candidate_id"] == "cand_apply"


def test_import_narration_requires_text(tmp_path):
    module = load_webui_host()

    with pytest.raises(ValueError, match="text is required"):
        module.import_local_narration(root=tmp_path, tenant_id=None, payload={"text": "  "})


def test_local_chat_turn_calls_chat_service_without_browser_token(monkeypatch, tmp_path):
    module = load_webui_host()
    calls = []

    def fake_get_llm_client(provider=None):
        calls.append(("provider", provider))
        return SimpleNamespace(provider=provider or "mock")

    def fake_run_turn(**kwargs):
        calls.append(("run_turn", kwargs))
        return {
            "request": {"retrieval_package": {"scene_id": kwargs["scene_id"]}},
            "response": {"text": "local skill reply", "speaker_person_id": "skill"},
            "event_id": "evt_local",
            "snapshot_id": "snap_local",
            "applied_patch_count": 1,
        }

    monkeypatch.setattr(module, "get_llm_client", fake_get_llm_client)
    monkeypatch.setattr(module, "run_turn", fake_run_turn)

    result = module.run_local_chat_turn(
        root=tmp_path,
        tenant_id=None,
        provider=None,
        adapter="claude",
        payload={"scene_id": "scene_workroom", "input": "你好"},
    )

    assert result["mode"] == "local_skill"
    assert result["provider"] == "mock"
    assert result["text"] == "local skill reply"
    assert result["event_id"] == "evt_local"
    assert result["retrieval_package"] == {"scene_id": "scene_workroom"}
    assert calls[0] == ("provider", None)
    run_call = calls[1][1]
    assert run_call["scene_id"] == "scene_workroom"
    assert run_call["user_input"] == "你好"
    assert "token" not in run_call


def test_local_chat_turn_requires_scene_and_input(tmp_path):
    module = load_webui_host()
    with pytest.raises(ValueError, match="scene_id"):
        module.run_local_chat_turn(
            root=tmp_path,
            tenant_id=None,
            provider=None,
            adapter="claude",
            payload={"input": "hello"},
        )

    with pytest.raises(ValueError, match="input"):
        module.run_local_chat_turn(
            root=tmp_path,
            tenant_id=None,
            provider=None,
            adapter="claude",
            payload={"scene_id": "scene_workroom", "input": ""},
        )
