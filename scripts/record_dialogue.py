import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.services.dialogue_service import record_dialogue_event
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a dialogue event")
    parser.add_argument("--root", default=str(ROOT), help="Project root")
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--user-input", required=True)
    parser.add_argument("--response-text", required=True)
    parser.add_argument("--speaker", action="append", default=[], help="Speaking person IDs")
    args = parser.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    result = record_dialogue_event(
        db_path=db_path,
        scene_id=args.scene_id,
        user_input=args.user_input,
        response_text=args.response_text,
        speaking_person_ids=args.speaker or [],
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
