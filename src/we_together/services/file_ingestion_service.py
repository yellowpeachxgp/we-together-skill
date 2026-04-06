from pathlib import Path

from we_together.importers.file_auto_importer import detect_file_mode
from we_together.services.auto_ingestion_service import auto_ingest_text
from we_together.services.email_ingestion_service import ingest_email_file


def ingest_file_auto(db_path: Path, file_path: Path) -> dict:
    mode = detect_file_mode(file_path)
    if mode == "email":
        result = ingest_email_file(db_path=db_path, email_path=file_path)
    else:
        text = file_path.read_text(encoding="utf-8")
        result = auto_ingest_text(db_path=db_path, text=text, source_name=file_path.name)
        return {"mode": mode, "content_mode": result["mode"], **{k: v for k, v in result.items() if k != "mode"}}
    return {"mode": mode, **result}
