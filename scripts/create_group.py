from pathlib import Path
import sys
import argparse
import json


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.services.group_service import create_group, add_group_member


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a group and optional members in the SQLite graph")
    parser.add_argument("--root", default=str(ROOT), help="Project root containing db/main.sqlite3")
    parser.add_argument("--group-type", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--member", action="append", default=[])
    args = parser.parse_args()

    db_path = Path(args.root) / "db" / "main.sqlite3"
    group_id = create_group(
        db_path=db_path,
        group_type=args.group_type,
        name=args.name,
        summary=args.summary,
    )
    member_count = 0
    for member in args.member:
        if ":" in member:
            person_id, role_label = member.split(":", 1)
        else:
            person_id, role_label = member, "member"
        add_group_member(
            db_path=db_path,
            group_id=group_id,
            person_id=person_id,
            role_label=role_label,
        )
        member_count += 1

    print(json.dumps({"group_id": group_id, "member_count": member_count}, ensure_ascii=False))
