from pathlib import Path

from we_together.importers.email_importer import import_email_file


def test_import_email_file_extracts_sender_subject_and_body(tmp_path):
    eml_path = tmp_path / "sample.eml"
    eml_path.write_text(
        "From: Alice <alice@example.com>\n"
        "To: Bob <bob@example.com>\n"
        "Subject: Project Update\n"
        "Date: Mon, 06 Apr 2026 10:00:00 +0800\n"
        "Content-Type: text/plain; charset=utf-8\n"
        "\n"
        "今天的项目推进顺利。\n",
        encoding="utf-8",
    )

    result = import_email_file(eml_path)

    assert result["raw_evidences"]
    assert result["identity_candidates"]
    assert result["event_candidates"]
    assert any(item["display_name"] == "Alice" for item in result["identity_candidates"])
    assert any("Project Update" in item["summary"] for item in result["event_candidates"])
