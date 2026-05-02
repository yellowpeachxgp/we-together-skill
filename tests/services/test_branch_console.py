import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from we_together.db.bootstrap import bootstrap_project  # noqa: E402


def _create_open_branch(db_path, branch_id, candidates):
    c = sqlite3.connect(db_path)
    c.execute(
        """INSERT INTO local_branches(branch_id, scope_type, scope_id, status,
           reason, created_at)
           VALUES(?, 'person', 'p_ambig', 'open', 'test', datetime('now'))""",
        (branch_id,),
    )
    for cid, label, score in candidates:
        c.execute(
            """INSERT INTO branch_candidates(candidate_id, branch_id, label,
               confidence, payload_json, status, created_at)
               VALUES(?, ?, ?, ?, '{}', 'open', datetime('now'))""",
            (cid, branch_id, label, score),
        )
    c.commit()
    c.close()


def test_list_open_branches_returns_candidates(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _create_open_branch(db_path, "br_1", [("c_merge", "merge", 0.6), ("c_new", "new", 0.4)])

    from branch_console import list_open_branches
    rows = list_open_branches(db_path)
    assert len(rows) == 1
    assert rows[0]["branch_id"] == "br_1"
    labels = {c["label"] for c in rows[0]["candidates"]}
    assert labels == {"merge", "new"}


def test_resolve_branch_manually_changes_status(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _create_open_branch(db_path, "br_2", [("c_a", "a", 0.5), ("c_b", "b", 0.5)])

    from branch_console import resolve_branch_manually
    result = resolve_branch_manually(db_path, "br_2", "c_a")
    assert result["resolved"]

    c = sqlite3.connect(db_path)
    status = c.execute(
        "SELECT status FROM local_branches WHERE branch_id = 'br_2'"
    ).fetchone()[0]
    c.close()
    assert status == "resolved"
