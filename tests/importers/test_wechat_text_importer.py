import csv
import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.importers.wechat_text_importer import import_wechat_text
from we_together.services.fusion_service import fuse_all


def _make_csv(tmp_path, rows):
    p = tmp_path / "wx.csv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["time", "sender", "content"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return p


def test_import_wechat_csv_creates_candidates(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    csv_path = _make_csv(tmp_path, [
        {"time": "2026-04-01 10:00:00", "sender": "Alice", "content": "吃饭了吗？"},
        {"time": "2026-04-01 10:01:00", "sender": "Bob", "content": "还没。"},
        {"time": "2026-04-01 10:02:00", "sender": "Alice", "content": "一起吧。"},
        {"time": "2026-04-01 10:03:00", "sender": "Bob", "content": "好。"},
    ])

    result = import_wechat_text(db_path=db_path, csv_path=csv_path, chat_name="alice-bob")

    assert result["messages"] == 4
    assert result["senders"] == 2
    assert result["relation_clues"] == 1
    assert result["group_clue_id"] is None

    conn = sqlite3.connect(db_path)
    idc_count = conn.execute("SELECT COUNT(*) FROM identity_candidates").fetchone()[0]
    evc_count = conn.execute("SELECT COUNT(*) FROM event_candidates").fetchone()[0]
    rlc_count = conn.execute("SELECT COUNT(*) FROM relation_clues").fetchone()[0]
    ev_count = conn.execute("SELECT COUNT(*) FROM raw_evidences").fetchone()[0]
    conn.close()
    assert (idc_count, evc_count, rlc_count, ev_count) == (2, 4, 1, 4)


def test_import_wechat_group_chat_creates_group_clue(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    csv_path = _make_csv(tmp_path, [
        {"time": "2026-04-01 10:00:00", "sender": "Alice", "content": "早"},
        {"time": "2026-04-01 10:01:00", "sender": "Bob", "content": "早"},
        {"time": "2026-04-01 10:02:00", "sender": "Carol", "content": "早"},
        {"time": "2026-04-01 10:03:00", "sender": "Alice", "content": "今天 sync"},
    ])

    result = import_wechat_text(db_path=db_path, csv_path=csv_path, chat_name="产品核心群")

    assert result["senders"] == 3
    assert result["group_clue_id"] is not None
    conn = sqlite3.connect(db_path)
    group_name = conn.execute(
        "SELECT group_name_hint FROM group_clues WHERE clue_id = ?",
        (result["group_clue_id"],),
    ).fetchone()[0]
    conn.close()
    assert group_name == "产品核心群"


def test_wechat_import_followed_by_fusion_creates_persons(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    csv_path = _make_csv(tmp_path, [
        {"time": "2026-04-01 10:00", "sender": "Alice", "content": "hi"},
        {"time": "2026-04-01 10:01", "sender": "Bob", "content": "hi"},
    ])
    import_wechat_text(db_path=db_path, csv_path=csv_path, chat_name="alice-bob")

    # 准备一个挂载 event
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO events(event_id, event_type, source_type, timestamp, summary,
                           visibility_level, confidence, is_structured,
                           raw_evidence_refs_json, metadata_json, created_at)
        VALUES('evt_wx_seed', 'narration_seed', 'manual', datetime('now'),
               '', 'visible', 0.8, 0, '[]', '{}', datetime('now'))
        """
    )
    conn.commit()
    conn.close()

    out = fuse_all(db_path, source_event_id="evt_wx_seed")
    assert out["identity"]["created_persons"] == 2
    assert out["relation"]["created_relations"] >= 1
