from pathlib import Path
import sys
import argparse
import json


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.services.scene_service import create_scene, add_scene_participant


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a scene in the SQLite graph")
    parser.add_argument("--root", default=str(ROOT), help="Project root containing db/main.sqlite3")
    parser.add_argument("--scene-type", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--location-scope", default=None)
    parser.add_argument("--channel-scope", default=None)
    parser.add_argument("--visibility-scope", default=None)
    parser.add_argument("--time-scope", default=None)
    parser.add_argument("--participant", action="append", default=[])
    args = parser.parse_args()

    root = Path(args.root)
    db_path = root / "db" / "main.sqlite3"
    environment = {
        "location_scope": args.location_scope,
        "channel_scope": args.channel_scope,
        "visibility_scope": args.visibility_scope,
        "time_scope": args.time_scope,
    }
    scene_id = create_scene(
        db_path=db_path,
        scene_type=args.scene_type,
        scene_summary=args.summary,
        environment=environment,
    )
    for participant in args.participant:
        add_scene_participant(
            db_path=db_path,
            scene_id=scene_id,
            person_id=participant,
            activation_state="explicit",
            activation_score=1.0,
            is_speaking=True,
        )

    print(json.dumps({"scene_id": scene_id}, ensure_ascii=False))
