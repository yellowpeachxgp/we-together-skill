from pathlib import Path

from we_together.importers.auto_importer import detect_import_mode
from we_together.services.ingestion_service import ingest_narration, ingest_text_chat


def auto_ingest_text(db_path: Path, text: str, source_name: str) -> dict:
    mode = detect_import_mode(text)
    if mode == "text_chat":
        result = ingest_text_chat(db_path=db_path, transcript=text, source_name=source_name)
    else:
        result = ingest_narration(db_path=db_path, text=text, source_name=source_name)
    return {"mode": mode, **result}
