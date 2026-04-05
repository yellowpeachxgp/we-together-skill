from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path
    db_dir: Path
    data_dir: Path


def build_app_paths(root: Path) -> AppPaths:
    return AppPaths(
        root=root,
        db_dir=root / "db",
        data_dir=root / "data",
    )
