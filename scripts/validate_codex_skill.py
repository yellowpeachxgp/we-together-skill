from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.packaging.codex_skill_support import (
    DEFAULT_CODEX_SKILL_NAME,
    DEFAULT_MCP_SERVER_NAME,
    codex_config_has_mcp_server,
    default_codex_skill_target,
    validate_codex_skill_family,
    validate_codex_skill_tree,
)


def _source_status(skill_dir: Path) -> dict:
    report = validate_codex_skill_tree(skill_dir, require_local_runtime=False)
    return {
        "checked": True,
        "ok": report["ok"],
        "skill_dir": report["skill_dir"],
        "missing": report["missing"],
        "invalid": report.get("invalid", []),
        "warnings": report.get("warnings", []),
    }


def _install_status(skill_dir: Path, *, installed: bool) -> dict:
    if not installed:
        return {
            "checked": False,
            "ok": None,
            "skill_dir": str(skill_dir),
            "missing": [],
        }

    report = validate_codex_skill_tree(skill_dir, require_local_runtime=True)
    return {
        "checked": True,
        "ok": report["ok"],
        "skill_dir": report["skill_dir"],
        "missing": report["missing"],
        "invalid": report.get("invalid", []),
        "warnings": report.get("warnings", []),
    }


def _config_status(
    config_path: Path,
    *,
    mcp_server_name: str,
    installed: bool,
) -> dict:
    if not installed:
        return {
            "checked": False,
            "ok": None,
            "config_path": str(config_path),
            "mcp_server_name": mcp_server_name,
            "registered": None,
        }

    registered = codex_config_has_mcp_server(config_path, mcp_server_name)
    return {
        "checked": True,
        "ok": registered,
        "config_path": str(config_path),
        "mcp_server_name": mcp_server_name,
        "registered": registered,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate we-together Codex skill layout")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--skill-dir", default=None)
    parser.add_argument("--installed", action="store_true")
    parser.add_argument("--family", action="store_true")
    parser.add_argument(
        "--config-path",
        default=str(Path.home() / ".codex" / "config.toml"),
    )
    parser.add_argument("--mcp-server-name", default=DEFAULT_MCP_SERVER_NAME)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    config_path = Path(args.config_path).expanduser().resolve()

    if args.family:
        if args.skill_dir:
            target_root = Path(args.skill_dir).expanduser().resolve()
        elif args.installed:
            target_root = default_codex_skill_target(skill_name=DEFAULT_CODEX_SKILL_NAME).parent
        else:
            target_root = repo_root

        family_report = validate_codex_skill_family(
            target_root,
            config_path=config_path,
            mcp_server_name=args.mcp_server_name,
        )
        report = {
            "action": "validate_codex_skill_family",
            "mode": "installed-family" if args.installed else "source-family",
            **family_report,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1

    if args.skill_dir:
        skill_dir = Path(args.skill_dir).expanduser().resolve()
    elif args.installed:
        skill_dir = default_codex_skill_target(skill_name=DEFAULT_CODEX_SKILL_NAME)
    else:
        skill_dir = repo_root / "codex_skill"

    source = _source_status(skill_dir)
    install = _install_status(
        skill_dir,
        installed=args.installed,
    )
    config = _config_status(
        config_path,
        mcp_server_name=args.mcp_server_name,
        installed=args.installed,
    )
    overall_ok = source["ok"] and (
        install["ok"] if install["checked"] else True
    ) and (
        config["ok"] if config["checked"] else True
    )

    report = {
        "mode": "installed" if args.installed else "source",
        "installed": args.installed,
        "skill_dir": str(skill_dir),
        "source": source,
        "install": install,
        "config": config,
        "missing": install["missing"] if install["checked"] else source["missing"],
        "invalid": install["invalid"] if install["checked"] else source["invalid"],
        "warnings": (source["warnings"] + install["warnings"])
        if install["checked"]
        else source["warnings"],
        "config_path": str(config_path),
        "mcp_server_name": args.mcp_server_name,
        "mcp_registered": config["registered"],
        "ok": overall_ok,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
