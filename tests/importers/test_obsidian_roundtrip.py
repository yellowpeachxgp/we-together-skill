from pathlib import Path

from we_together.db.bootstrap import bootstrap_project
from we_together.importers.obsidian_md_importer import import_obsidian_vault
from we_together.services.obsidian_exporter import export_to_obsidian_vault


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Alice.md").write_text(
        "---\ntype: person\n---\n\nAlice is a project manager.\n"
        "She works with [[Bob]] and [[Carol]].\n"
    )
    (vault / "Bob.md").write_text(
        "Bob is an engineer. Close friend with [[Alice]].\n"
    )
    (vault / "Carol.md").write_text(
        "---\ntype: person\n---\n\nCarol is a designer.\n"
    )
    (vault / "draft.md").write_text("---\ntype: skip\n---\n\njust a draft\n")
    return vault


def test_obsidian_import_extracts_people(tmp_path):
    vault = _make_vault(tmp_path)
    result = import_obsidian_vault(vault)
    names = {c["display_name"] for c in result["identity_candidates"]}
    assert {"Alice", "Bob", "Carol"} <= names
    # skip 的 draft 不应出现
    assert "draft" not in names


def test_obsidian_import_extracts_mentions():
    from pathlib import Path as _P
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        vault = _make_vault(_P(tmp))
        result = import_obsidian_vault(vault)
        pairs = {(c["a"], c["b"]) for c in result["relation_clues"]}
        assert ("Alice", "Bob") in pairs
        assert ("Alice", "Carol") in pairs


def test_obsidian_exporter_writes_md(tmp_path, temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    import sqlite3
    c = sqlite3.connect(db)
    c.execute(
        "INSERT INTO persons(person_id, primary_name, status, persona_summary, "
        "confidence, metadata_json, created_at, updated_at) VALUES("
        "'p_ob','ObAlice','active','工程师',0.8,'{}',datetime('now'),datetime('now'))"
    )
    c.commit(); c.close()

    vault = tmp_path / "out"
    r = export_to_obsidian_vault(db, vault)
    assert r["exported_count"] == 1
    assert (vault / "ObAlice.md").exists()
    content = (vault / "ObAlice.md").read_text()
    assert "工程师" in content
