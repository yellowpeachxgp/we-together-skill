from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.packaging.codex_skill_support import (
    DEFAULT_CODEX_SKILL_NAME,
    DEFAULT_MCP_SERVER_NAME,
)


SCRIPT_REPO_ROOT = Path(__file__).resolve().parents[1]


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _resolve_repo_root(raw_value: str | None) -> Path:
    cleaned = _clean_optional_text(raw_value)
    if cleaned is None:
        return SCRIPT_REPO_ROOT.resolve()
    return Path(cleaned).expanduser().resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Force-update the installed we-together Codex native skill",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--repo-root",
        default=str(SCRIPT_REPO_ROOT),
        help="Repository root used for source discovery and generated runtime references",
    )
    parser.add_argument(
        "--source-dir",
        default=None,
        help="Optional source skill directory; defaults to <repo-root>/codex_skill",
    )
    parser.add_argument(
        "--target-dir",
        default=None,
        help="Optional install target directory; defaults to ~/.codex/skills/<skill-name>",
    )
    parser.add_argument(
        "--skill-name",
        default=DEFAULT_CODEX_SKILL_NAME,
        help="Installed skill directory name under ~/.codex/skills",
    )
    parser.add_argument(
        "--mcp-server-name",
        default=DEFAULT_MCP_SERVER_NAME,
        help="MCP server name written into generated local-runtime references",
    )
    parser.add_argument(
        "--family",
        action="store_true",
        help="Update the router plus dev/runtime/ingest sub-skills together",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and print the install action without modifying the installed skill",
    )
    args = parser.parse_args()

    repo_root = _resolve_repo_root(args.repo_root)
    source_dir = _clean_optional_text(args.source_dir)
    target_dir = _clean_optional_text(args.target_dir)
    skill_name = _clean_optional_text(args.skill_name) or DEFAULT_CODEX_SKILL_NAME
    mcp_server_name = (
        _clean_optional_text(args.mcp_server_name) or DEFAULT_MCP_SERVER_NAME
    )

    cmd = [
        sys.executable,
        str(Path(__file__).resolve().with_name("install_codex_skill.py")),
        "--repo-root",
        str(repo_root),
        "--skill-name",
        skill_name,
        "--mcp-server-name",
        mcp_server_name,
        "--force",
    ]
    if source_dir is not None:
        cmd.extend(["--source-dir", source_dir])
    if target_dir is not None:
        cmd.extend(["--target-dir", target_dir])
    if args.family:
        cmd.append("--family")
    if args.dry_run:
        cmd.append("--dry-run")

    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
