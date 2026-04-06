from we_together.importers.text_chat_importer import import_text_chat


def test_import_text_chat_extracts_speakers_and_events():
    transcript = """2026-04-06 23:10 小王: 今天好累
2026-04-06 23:11 小李: 早点休息
"""

    result = import_text_chat(transcript=transcript, source_name="chat.txt")

    speaker_names = {item["display_name"] for item in result["identity_candidates"]}
    assert "小王" in speaker_names
    assert "小李" in speaker_names
    assert len(result["event_candidates"]) >= 2
