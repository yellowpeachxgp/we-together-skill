from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.db.bootstrap import bootstrap_project


if __name__ == "__main__":
    bootstrap_project(ROOT)
    print("bootstrap complete")
