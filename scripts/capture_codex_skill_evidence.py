from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.packaging.codex_skill_evidence import collect_codex_skill_evidence


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan Codex session logs and summarize we-together skill-hit evidence",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--session-root",
        default=str(Path.home() / ".codex" / "sessions"),
        help="Codex session log root to scan",
    )
    parser.add_argument(
        "--skill",
        action="append",
        default=None,
        help="Skill name to include; repeat to filter multiple skills",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only inspect the newest N session logs",
    )
    args = parser.parse_args()

    report = collect_codex_skill_evidence(
        Path(args.session_root),
        skill_names=args.skill,
        limit=args.limit,
    )
    print(
        json.dumps(
            {
                "action": "capture_codex_skill_evidence",
                **report,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
