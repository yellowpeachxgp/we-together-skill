from pathlib import Path

from we_together.importers.file_auto_importer import detect_file_mode


def test_detect_file_mode_returns_email_for_eml(tmp_path):
    eml = tmp_path / "sample.eml"
    eml.write_text("From: a@example.com\n\nbody", encoding="utf-8")
    assert detect_file_mode(eml) == "email"


def test_detect_file_mode_returns_text_for_txt(tmp_path):
    txt = tmp_path / "sample.txt"
    txt.write_text("小王和小李以前是同事，现在还是朋友。", encoding="utf-8")
    assert detect_file_mode(txt) == "text"
