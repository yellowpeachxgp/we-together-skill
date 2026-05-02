"""Document importer：PDF / DOCX / 纯文本。

延迟 import pypdf / python-docx。纯文本不需要外部库。
"""
from __future__ import annotations

from pathlib import Path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pypdf not installed: pip install pypdf") from exc
    reader = PdfReader(str(path))
    return "\n\n".join((p.extract_text() or "") for p in reader.pages)


def _read_docx(path: Path) -> str:
    try:
        import docx  # type: ignore  # python-docx
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("python-docx not installed: pip install python-docx") from exc
    doc = docx.Document(str(path))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text)


def import_document(doc_path: Path, *, max_chars: int = 8000) -> dict:
    if not doc_path.exists():
        raise FileNotFoundError(f"document not found: {doc_path}")
    suffix = doc_path.suffix.lower()
    if suffix == ".pdf":
        text = _read_pdf(doc_path)
    elif suffix in (".docx",):
        text = _read_docx(doc_path)
    elif suffix in (".txt", ".md"):
        text = _read_text(doc_path)
    else:
        raise ValueError(f"unsupported document type: {suffix}")

    text = text[:max_chars]
    return {
        "identity_candidates": [],
        "event_candidates": [
            {
                "summary": text[:500] or "[empty document]",
                "event_type": "document_event",
                "timestamp": None,
                "confidence": 0.6,
                "source": "document_importer",
                "document_path": str(doc_path),
                "document_suffix": suffix,
                "char_count": len(text),
            }
        ],
        "source": "document_importer",
        "full_text": text,
    }
