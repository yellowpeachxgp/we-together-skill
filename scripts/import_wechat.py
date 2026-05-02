"""微信 CSV 导入 CLI。

读取 (time, sender, content) 列的 CSV → candidate 层 → 可选 fuse_all。

用法:
  .venv/bin/python scripts/import_wechat.py --root . --tenant-id alpha --file ./wx.csv [--chat-name "群名"] [--fuse]
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

from we_together.importers.wechat_text_importer import import_wechat_text
from we_together.services.fusion_service import fuse_all
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    parser = argparse.ArgumentParser(description="微信 CSV 导入")
    parser.add_argument("--root", default=str(ROOT), help="Project root containing db/main.sqlite3")
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--file", required=True, help="CSV 文件路径")
    parser.add_argument("--chat-name", default=None, help="聊天名称（含'群'/'group'触发 group_clue）")
    parser.add_argument("--fuse", action="store_true",
                        help="导入后自动跑 fusion 落主图")
    args = parser.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    csv_path = Path(args.file)
    if not csv_path.exists():
        print(f"file not found: {csv_path}", file=sys.stderr)
        raise SystemExit(2)

    result = import_wechat_text(db_path=db_path, csv_path=csv_path,
                                 chat_name=args.chat_name)

    fuse_result = None
    if args.fuse:
        # fusion 需要一个 source event 作为 link 节点
        import sqlite3
        from datetime import UTC, datetime
        eid = f"evt_wx_import_{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT INTO events(event_id, event_type, source_type, timestamp, summary,
                               visibility_level, confidence, is_structured,
                               raw_evidence_refs_json, metadata_json, created_at)
            VALUES(?, 'narration_seed', 'manual', ?, 'wechat import seed',
                   'visible', 0.7, 0, '[]', '{}', ?)
            """,
            (eid, now, now),
        )
        conn.commit()
        conn.close()
        fuse_result = fuse_all(db_path, source_event_id=eid)

    print(json.dumps({
        "import": result,
        "fusion": fuse_result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
