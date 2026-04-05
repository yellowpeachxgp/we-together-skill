from pathlib import Path
import sys
import argparse


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.db.bootstrap import bootstrap_project


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap we_together runtime directories and database")
    parser.add_argument("--root", default=str(ROOT), help="Project root for runtime data and database")
    args = parser.parse_args()

    bootstrap_project(Path(args.root))
    print("bootstrap complete")
