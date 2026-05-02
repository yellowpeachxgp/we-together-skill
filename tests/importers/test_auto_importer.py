from we_together.importers.auto_importer import detect_import_mode


def test_detect_import_mode_prefers_text_chat_for_timestamped_transcript():
    transcript = "2026-04-06 23:10 小王: 今天好累\n2026-04-06 23:11 小李: 早点休息\n"
    assert detect_import_mode(transcript) == "text_chat"


def test_detect_import_mode_falls_back_to_narration_for_plain_text():
    text = "小王和小李以前是同事，现在还是朋友。"
    assert detect_import_mode(text) == "narration"
