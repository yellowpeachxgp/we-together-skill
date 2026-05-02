"""迁移 CLI：csv / notion / signal 三种分派。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.importers.migration_importer import (
    import_csv,
    import_notion_export,
    import_signal_export,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["csv", "notion", "signal"], required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--source-name", default=None)
    args = ap.parse_args()

    path = Path(args.input).resolve()
    if args.format == "csv":
        r = import_csv(path, source_name=args.source_name)
    elif args.format == "notion":
        r = import_notion_export(path)
    else:
        r = import_signal_export(path)

    out = {k: v for k, v in r.items() if k != "full_text"}
    out["identity_count"] = len(out.get("identity_candidates", []))
    out["event_count"] = len(out.get("event_candidates", []))
    print(json.dumps({k: v for k, v in out.items() if not isinstance(v, list)},
                      ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
