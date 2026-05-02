from we_together.importers.text_narration_importer import import_narration_text


def test_import_narration_text_returns_import_result_shape():
    result = import_narration_text(
        text="小王和小李以前是同事，现在还是朋友。",
        source_name="manual-note",
    )

    assert "raw_evidences" in result
    assert "identity_candidates" in result
    assert "event_candidates" in result
    assert "relation_clues" in result
