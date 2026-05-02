import sqlite3
from pathlib import Path

from we_together.importers.imessage_importer import import_imessage_db
from we_together.importers.mbox_importer import import_mbox
from we_together.importers.wechat_db_importer import import_wechat_db


def _make_imessage_fixture(path: Path) -> None:
    c = sqlite3.connect(path)
    c.executescript(
        """
        CREATE TABLE handle (ROWID INTEGER PRIMARY KEY, id TEXT, service TEXT);
        CREATE TABLE message (ROWID INTEGER PRIMARY KEY, guid TEXT, text TEXT,
                              handle_id INTEGER, date INTEGER, is_from_me INTEGER);
        CREATE TABLE chat (ROWID INTEGER PRIMARY KEY, guid TEXT, display_name TEXT);
        INSERT INTO handle(ROWID, id, service) VALUES(1, '+15551234', 'iMessage');
        INSERT INTO handle(ROWID, id, service) VALUES(2, 'bob@apple.com', 'iMessage');
        INSERT INTO message(ROWID, guid, text, handle_id, date, is_from_me)
          VALUES (1, 'g1', 'hi alice', 1, 1000, 0);
        INSERT INTO message(ROWID, guid, text, handle_id, date, is_from_me)
          VALUES (2, 'g2', 'hi bob', 2, 1001, 1);
        """
    )
    c.commit()
    c.close()


def _make_wechat_fixture(path: Path) -> None:
    c = sqlite3.connect(path)
    c.executescript(
        """
        CREATE TABLE contact (wxid TEXT PRIMARY KEY, nickname TEXT, remark TEXT);
        CREATE TABLE message (msg_id TEXT PRIMARY KEY, wxid TEXT, content TEXT,
                              createTime INTEGER, is_send INTEGER, room_id TEXT);
        INSERT INTO contact VALUES('wx_alice', 'Alice', '爱');
        INSERT INTO contact VALUES('wx_bob', 'Bob', NULL);
        INSERT INTO message VALUES('m1', 'wx_alice', '下午见', 1000, 0, NULL);
        INSERT INTO message VALUES('m2', 'wx_bob', '好的', 1001, 0, NULL);
        """
    )
    c.commit()
    c.close()


def test_imessage_importer_reads_candidates(tmp_path):
    db = tmp_path / "chat.db"
    _make_imessage_fixture(db)
    result = import_imessage_db(db)
    assert len(result["identity_candidates"]) == 2
    assert len(result["event_candidates"]) == 2
    assert any(e["summary"] == "hi alice" for e in result["event_candidates"])


def test_wechat_db_importer_reads_candidates(tmp_path):
    db = tmp_path / "wechat.db"
    _make_wechat_fixture(db)
    result = import_wechat_db(db)
    assert len(result["identity_candidates"]) == 2
    assert any(c["display_name"] == "爱" for c in result["identity_candidates"])
    assert len(result["event_candidates"]) == 2


def test_mbox_importer_reads_mailbox(tmp_path):
    mbox_path = tmp_path / "sample.mbox"
    mbox_path.write_text(
        "From alice@example.com Mon Apr 01 12:00:00 2024\n"
        "From: alice@example.com\n"
        "To: bob@example.com\n"
        "Subject: Hello\n"
        "Date: Mon, 01 Apr 2024 12:00:00 +0000\n"
        "\n"
        "body text here\n"
        "\n"
        "From bob@example.com Mon Apr 02 13:00:00 2024\n"
        "From: bob@example.com\n"
        "To: alice@example.com\n"
        "Subject: Re: Hello\n"
        "Date: Tue, 02 Apr 2024 13:00:00 +0000\n"
        "\n"
        "reply body\n"
    )
    result = import_mbox(mbox_path)
    assert len(result["event_candidates"]) == 2
    subjects = {e["subject"] for e in result["event_candidates"]}
    assert "Hello" in subjects
