from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.packaging.codex_skill_support import (
    DEFAULT_CODEX_SKILL_NAME,
    DEFAULT_MCP_SERVER_NAME,
    GENERATED_LOCAL_RUNTIME_FILES,
    default_codex_skill_target,
    install_codex_skill_family,
    install_codex_skill,
)


SCRIPT_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_SUBDIR = "codex_skill"


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _resolve_optional_path(
    raw_value: str | None,
    *,
    default_path: Path,
) -> Path:
    cleaned = _clean_optional_text(raw_value)
    if cleaned is None:
        return default_path.resolve()
    return Path(cleaned).expanduser().resolve()


def _build_output_payload(
    *,
    report: dict,
    skill_name: str,
    force: bool,
    dry_run: bool,
) -> dict:
    mode = "dry-run" if dry_run else "install"
    return {
        "ok": report["ok"],
        "action": "install_codex_skill",
        "mode": mode,
        "skill_name": skill_name,
        "source_dir": report["source_dir"],
        "target_dir": report["target_dir"],
        "repo_root": report["repo_root"],
        "mcp_server_name": report["mcp_server_name"],
        "force": force,
        "dry_run": dry_run,
        "generated_runtime_files": GENERATED_LOCAL_RUNTIME_FILES,
        "report": report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install the we-together Codex native skill",
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
        help="Install the router plus dev/runtime/ingest sub-skills into the target skills directory",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing installed skill directory if it already exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve paths and print the install plan without writing files",
    )
    args = parser.parse_args()

    repo_root = _resolve_optional_path(args.repo_root, default_path=SCRIPT_REPO_ROOT)
    skill_name = _clean_optional_text(args.skill_name) or DEFAULT_CODEX_SKILL_NAME
    mcp_server_name = (
        _clean_optional_text(args.mcp_server_name) or DEFAULT_MCP_SERVER_NAME
    )
    if args.family:
        target_root = _resolve_optional_path(
            args.target_dir,
            default_path=default_codex_skill_target(skill_name=skill_name).parent,
        )
        report = install_codex_skill_family(
            repo_root,
            target_root=target_root,
            mcp_server_name=mcp_server_name,
            force=args.force,
            dry_run=args.dry_run,
        )
        payload = {
            "ok": report["ok"],
            "action": "install_codex_skill_family",
            "mode": "dry-run" if args.dry_run else "install",
            "target_root": report["target_root"],
            "repo_root": report["repo_root"],
            "mcp_server_name": report["mcp_server_name"],
            "force": args.force,
            "dry_run": args.dry_run,
            "skills": report["skills"],
            "missing_sources": report["missing_sources"],
            "reports": report["reports"],
        }
    else:
        source_dir = _resolve_optional_path(
            args.source_dir,
            default_path=repo_root / DEFAULT_SOURCE_SUBDIR,
        )
        target_dir = _resolve_optional_path(
            args.target_dir,
            default_path=default_codex_skill_target(skill_name=skill_name),
        )

        report = install_codex_skill(
            source_dir,
            target_dir,
            repo_root=repo_root,
            mcp_server_name=mcp_server_name,
            force=args.force,
            dry_run=args.dry_run,
        )
        payload = _build_output_payload(
            report=report,
            skill_name=skill_name,
            force=args.force,
            dry_run=args.dry_run,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
