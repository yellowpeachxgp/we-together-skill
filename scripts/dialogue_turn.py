import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.services.dialogue_service import process_dialogue_turn
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    parser = argparse.ArgumentParser(description="对话轮次端到端处理")
    parser.add_argument("--root", default=str(ROOT), help="Project root")
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--user-input", required=True)
    parser.add_argument("--response-text", required=True)
    parser.add_argument("--speaking-person-ids", nargs="*", default=None)
    args = parser.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    result = process_dialogue_turn(
        db_path=db_path,
        scene_id=args.scene_id,
        user_input=args.user_input,
        response_text=args.response_text,
        speaking_person_ids=args.speaking_person_ids,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
