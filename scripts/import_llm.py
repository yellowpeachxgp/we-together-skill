"""LLM 驱动的 narration 导入 CLI。

链路：raw text → llm_extraction → candidate 层 → 可选 fuse_all 落主图

用法:
  WE_TOGETHER_LLM_PROVIDER=mock .venv/bin/python scripts/import_llm.py \
    --root . --tenant-id alpha --text "小王和小李是朋友" --source-name manual --fuse
"""
import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.llm import get_llm_client
from we_together.services.fusion_service import fuse_all
from we_together.services.llm_extraction_service import extract_candidates_from_text
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM 驱动的 narration 导入")
    parser.add_argument("--root", default=str(ROOT), help="Project root containing db/main.sqlite3")
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--text", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--fuse", action="store_true")
    args = parser.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    client = get_llm_client(args.provider)

    extract_result = extract_candidates_from_text(
        db_path=db_path, text=args.text, source_name=args.source_name,
        llm_client=client,
    )

    fuse_result = None
    if args.fuse:
        import sqlite3
        from datetime import UTC, datetime
        eid = f"evt_llm_import_{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT INTO events(event_id, event_type, source_type, timestamp, summary,
                               visibility_level, confidence, is_structured,
                               raw_evidence_refs_json, metadata_json, created_at)
            VALUES(?, 'narration_seed', 'llm', ?, 'llm import seed',
                   'visible', 0.7, 0, '[]', '{}', ?)
            """,
            (eid, now, now),
        )
        conn.commit()
        conn.close()
        fuse_result = fuse_all(db_path, source_event_id=eid)

    print(json.dumps({
        "extract": extract_result,
        "fusion": fuse_result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
