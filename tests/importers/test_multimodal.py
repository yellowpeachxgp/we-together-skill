from datetime import UTC, datetime
from pathlib import Path

from we_together.db.bootstrap import bootstrap_project
from we_together.importers.audio_importer import import_audio
from we_together.importers.document_importer import import_document
from we_together.importers.screenshot_series_importer import (
    import_screenshot_series,
)
from we_together.importers.video_importer import import_video
from we_together.llm.providers.audio import MockAudioTranscriber
from we_together.llm.providers.vision import MockVisionLLMClient
from we_together.services.evidence_dedup_service import (
    compute_audio_fingerprint,
    compute_image_phash,
    is_duplicate_audio,
    is_duplicate_image,
    phash_distance,
    register_audio_hash,
    register_image_hash,
)


# --- audio ---

def test_audio_importer_transcribes(tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF0000WAVEfmt fake")
    t = MockAudioTranscriber(scripted_transcripts=["今天开会讨论了产品规划"])
    result = import_audio(audio, t, language="zh")
    assert result["transcript_length"] > 0
    assert result["event_candidates"][0]["event_type"] == "audio_event"
    assert "今天开会" in result["event_candidates"][0]["summary"]


def test_audio_importer_missing_file(tmp_path):
    import pytest
    t = MockAudioTranscriber()
    with pytest.raises(FileNotFoundError):
        import_audio(tmp_path / "nope.wav", t)


# --- video ---

def test_video_importer_merges_timeline(tmp_path):
    f1 = tmp_path / "frame1.jpg"; f1.write_bytes(b"jpeg1")
    f2 = tmp_path / "frame2.jpg"; f2.write_bytes(b"jpeg2")
    audio = tmp_path / "audio.wav"; audio.write_bytes(b"wav")

    vc = MockVisionLLMClient(scripted_descriptions=["Alice 说话", "Bob 回应"])
    tr = MockAudioTranscriber(scripted_transcripts=["...对话转写..."])

    result = import_video(
        frames=[(0.0, f1), (1.5, f2)],
        audio_path=audio,
        vision_client=vc,
        audio_transcriber=tr,
    )
    assert result["frame_count"] == 2
    assert result["audio_transcript_length"] > 0
    # 时间戳升序
    tss = [e["timestamp"] for e in result["event_candidates"]]
    assert tss == sorted(tss)


def test_video_no_audio(tmp_path):
    f1 = tmp_path / "frame.jpg"; f1.write_bytes(b"j")
    vc = MockVisionLLMClient()
    result = import_video(frames=[(0.0, f1)], audio_path=None,
                           vision_client=vc, audio_transcriber=None)
    assert result["frame_count"] == 1
    assert result["audio_transcript_length"] == 0


# --- document ---

def test_document_importer_txt(tmp_path):
    txt = tmp_path / "note.txt"
    txt.write_text("Alice 和 Bob 开会讨论项目。")
    result = import_document(txt)
    assert result["event_candidates"][0]["event_type"] == "document_event"
    assert "Alice" in result["full_text"]
    assert result["event_candidates"][0]["document_suffix"] == ".txt"


def test_document_importer_md(tmp_path):
    md = tmp_path / "note.md"
    md.write_text("# Heading\n\n内容")
    result = import_document(md)
    assert result["event_candidates"][0]["document_suffix"] == ".md"


def test_document_unsupported(tmp_path):
    import pytest
    p = tmp_path / "x.bin"; p.write_bytes(b"bin")
    with pytest.raises(ValueError):
        import_document(p)


# --- screenshot ---

def test_screenshot_series_sorted(tmp_path):
    s1 = tmp_path / "s1.png"; s1.write_bytes(b"p1")
    s2 = tmp_path / "s2.png"; s2.write_bytes(b"p2")
    vc = MockVisionLLMClient(scripted_descriptions=["image a", "image b"])
    result = import_screenshot_series(
        screenshots=[(2.0, s2), (1.0, s1)],
        vision_client=vc,
    )
    assert result["screenshot_count"] == 2
    tss = [e["timestamp"] for e in result["event_candidates"]]
    assert tss == [1.0, 2.0]


# --- dedup multimodal ---

def test_image_phash_basic():
    ph = compute_image_phash(b"A" * 320)
    assert len(ph) == 64
    assert set(ph) <= {"0", "1"}


def test_phash_distance_identical():
    assert phash_distance("1010" * 16, "1010" * 16) == 0


def test_phash_distance_diff():
    assert phash_distance("0000" * 16, "1111" * 16) == 64


def test_image_dedup_registered(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    ph = compute_image_phash(b"\x10\x20\x30" * 30)
    assert not is_duplicate_image(db, ph)
    register_image_hash(db, ph, "ev_img_1", datetime.now(UTC).isoformat())
    assert is_duplicate_image(db, ph, threshold=0)


def test_audio_fingerprint_and_dedup(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    fp = compute_audio_fingerprint(b"wav_data" * 50)
    assert len(fp) == 32
    assert not is_duplicate_audio(db, fp)
    register_audio_hash(db, fp, "ev_aud_1", datetime.now(UTC).isoformat())
    assert is_duplicate_audio(db, fp, threshold=0)
