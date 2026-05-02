"""为指定 person_id（或全图）抽取 facets。

用法:
  .venv/bin/python scripts/extract_facets.py --root . --person-id person_x
  .venv/bin/python scripts/extract_facets.py --root . --all --limit 20
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.llm import get_llm_client
from we_together.services.facet_extraction_service import extract_facets_for_person
from we_together.services.tenant_router import resolve_tenant_root


def _list_active_persons(db_path: Path, limit: int) -> list[str]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT person_id FROM persons WHERE status = 'active' ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [row[0] for row in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM 驱动的 facet 抽取")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--tenant-id", default=None)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--person-id", help="针对单个 person_id")
    group.add_argument("--all", action="store_true", help="遍历全图 active persons")
    parser.add_argument("--limit", type=int, default=50, help="--all 模式下最大处理数")
    parser.add_argument("--max-events", type=int, default=20)
    parser.add_argument("--provider", default=None)
    args = parser.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    client = get_llm_client(args.provider)

    if args.person_id:
        targets = [args.person_id]
    else:
        targets = _list_active_persons(db_path, args.limit)

    out = []
    for pid in targets:
        try:
            res = extract_facets_for_person(
                db_path=db_path, person_id=pid,
                llm_client=client, max_events=args.max_events,
            )
            out.append(res)
        except ValueError as exc:
            out.append({"person_id": pid, "error": str(exc)})

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
