from pathlib import Path


def detect_file_mode(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".eml":
        return "email"
    return "text"
