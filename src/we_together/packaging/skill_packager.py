"""Skill 可分发包：把 SKILL.md + migrations/seeds + 选定脚本打包为 .weskill.zip。

最小 manifest 约定:
  {
    "format_version": 1,
    "name": "we-together",
    "skill_version": "0.19.0",
    "schema_version": "0021",
    "created_at": "...",
    "files": ["SKILL.md", "db/migrations/*", ...]
  }

使用 Python 内置 zipfile 实现，无外部依赖。
"""
from __future__ import annotations

import json
import re
import tomllib
import zipfile
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_INCLUDE_GLOBS = [
    "SKILL.md",
    "db/migrations/*.sql",
    "db/seeds/*.yaml",
    "db/seeds/*.yml",
    "db/seeds/*.json",
    "scripts/*.py",
    "src/we_together/**/*.py",
]

FORBIDDEN_PACKAGE_PARTS = {
    ".git",
    ".playwright-cli",
    ".serena",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "output",
}
FORBIDDEN_PACKAGE_FILENAMES = {
    ".env",
    ".env.local",
    ".pypirc",
    ".python-version",
    "id_rsa",
    "id_rsa.pub",
}
FORBIDDEN_PACKAGE_SUFFIXES = (
    ".DS_Store",
    ".db",
    ".db-shm",
    ".db-wal",
    ".key",
    ".pem",
    ".pyc",
    ".pyo",
    ".sqlite3",
    ".sqlite3-shm",
    ".sqlite3-wal",
    ".tar.gz",
    ".whl",
)

VERSION_RE = re.compile(r'^VERSION\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
DUnder_VERSION_RE = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def _collect_files(root: Path, globs: list[str]) -> list[Path]:
    files: list[Path] = []
    for g in globs:
        files.extend(sorted(root.glob(g)))
    # dedupe 保持相对顺序
    seen: set[Path] = set()
    out: list[Path] = []
    for f in files:
        if f.is_file() and f not in seen:
            seen.add(f)
            out.append(f)
    return out


def _is_forbidden_package_path(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/")
    parts = set(normalized.split("/"))
    filename = normalized.rsplit("/", 1)[-1]
    lowered = filename.lower()
    sensitive_name = any(token in lowered for token in ("secret", "token", "credential"))
    return (
        bool(parts & FORBIDDEN_PACKAGE_PARTS)
        or filename in FORBIDDEN_PACKAGE_FILENAMES
        or sensitive_name
        or normalized.endswith(FORBIDDEN_PACKAGE_SUFFIXES)
    )


def _unsafe_zip_member(name: str) -> bool:
    normalized = name.replace("\\", "/")
    return normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized or normalized in {"..", "."}


def _infer_skill_version(root: Path) -> str:
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        data = tomllib.loads(pyproject.read_text("utf-8"))
        version = data.get("project", {}).get("version")
        if version:
            return str(version)

    cli_py = root / "src" / "we_together" / "cli.py"
    if cli_py.exists():
        match = VERSION_RE.search(cli_py.read_text("utf-8"))
        if match:
            return match.group(1)

    init_py = root / "src" / "we_together" / "__init__.py"
    if init_py.exists():
        match = DUnder_VERSION_RE.search(init_py.read_text("utf-8"))
        if match:
            return match.group(1)

    return "0.8.0"


def _infer_schema_version(root: Path) -> str:
    migrations = sorted((root / "db" / "migrations").glob("*.sql"))
    prefixes = [p.name[:4] for p in migrations if len(p.name) >= 4 and p.name[:4].isdigit()]
    if prefixes:
        return max(prefixes)
    return "0007"


def pack_skill(
    root: Path,
    output_path: Path,
    *,
    skill_version: str | None = None,
    schema_version: str | None = None,
    include_globs: list[str] | None = None,
) -> dict:
    include_globs = include_globs or DEFAULT_INCLUDE_GLOBS
    skill_version = skill_version or _infer_skill_version(root)
    schema_version = schema_version or _infer_schema_version(root)
    files = _collect_files(root, include_globs)
    forbidden = sorted(
        str(f.relative_to(root))
        for f in files
        if _is_forbidden_package_path(str(f.relative_to(root)))
    )
    if forbidden:
        raise ValueError(f"forbidden package path(s): {', '.join(forbidden)}")
    manifest = {
        "format_version": 1,
        "name": "we-together",
        "skill_version": skill_version,
        "schema_version": schema_version,
        "created_at": datetime.now(UTC).isoformat(),
        "files": [str(f.relative_to(root)) for f in files],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for f in files:
            zf.write(f, arcname=str(f.relative_to(root)))
    return {"output": str(output_path), "file_count": len(files), "manifest": manifest}


def unpack_skill(package_path: Path, target_root: Path) -> dict:
    target_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package_path, "r") as zf:
        unsafe = sorted(name for name in zf.namelist() if _unsafe_zip_member(name))
        if unsafe:
            raise ValueError(f"unsafe zip member(s): {', '.join(unsafe)}")
        manifest_raw = zf.read("manifest.json").decode("utf-8")
        manifest = json.loads(manifest_raw)
        zf.extractall(target_root)
    return {"target": str(target_root), "manifest": manifest}
