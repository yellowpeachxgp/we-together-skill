from pathlib import Path

from we_together.services.file_ingestion_service import ingest_file_auto

SUPPORTED_SUFFIXES = {".txt", ".md", ".eml"}


def ingest_directory(db_path: Path, directory: Path) -> dict:
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    imported = []
    skipped = []
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            skipped.append(path.name)
            continue
        imported.append(ingest_file_auto(db_path=db_path, file_path=path))

    return {
        "file_count": len(imported),
        "skipped_count": len(skipped),
        "skipped_files": skipped,
        "results": imported,
    }
