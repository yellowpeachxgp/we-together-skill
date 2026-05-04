from __future__ import annotations

import json
import re
import shutil
import tomllib
from pathlib import Path

DEFAULT_CODEX_SKILL_NAME = "we-together"
DEFAULT_MCP_SERVER_NAME = "we-together-local-validate"
GENERATED_LOCAL_RUNTIME_FILES = [
    "references/local-runtime.md",
    "references/local-runtime.json",
]
DEFAULT_CODEX_SKILL_FAMILY = {
    "we-together": "codex_skill",
    "we-together-dev": "codex_skill_dev",
    "we-together-runtime": "codex_skill_runtime",
    "we-together-ingest": "codex_skill_ingest",
    "we-together-world": "codex_skill_world",
    "we-together-simulation": "codex_skill_simulation",
    "we-together-release": "codex_skill_release",
}
MANAGED_MCP_BLOCK_PREFIX = "# BEGIN we-together managed MCP server:"
MANAGED_MCP_BLOCK_SUFFIX = "# END we-together managed MCP server:"

REQUIRED_SOURCE_FILES = [
    "SKILL.md",
    "agents/openai.yaml",
    "prompts/dev.md",
    "prompts/runtime.md",
    "prompts/ingest.md",
    "references/triggers.md",
    "references/intent-examples.md",
    "references/local-runtime.template.md",
]


def default_codex_skill_target(
    *,
    home: Path | None = None,
    skill_name: str = DEFAULT_CODEX_SKILL_NAME,
) -> Path:
    home = (home or Path.home()).expanduser()
    return home / ".codex" / "skills" / skill_name


def discover_codex_skill_family_sources(repo_root: Path) -> dict[str, Path]:
    repo_root = Path(repo_root).resolve()
    discovered: dict[str, Path] = {}
    for skill_name, rel_dir in DEFAULT_CODEX_SKILL_FAMILY.items():
        source_dir = repo_root / rel_dir
        if source_dir.is_dir():
            discovered[skill_name] = source_dir
    return discovered


def _render_local_runtime_markdown(
    repo_root: Path,
    *,
    mcp_server_name: str,
    template_text: str = "",
) -> str:
    handoff = repo_root / "docs" / "HANDOFF.md"
    current_status = repo_root / "docs" / "superpowers" / "state" / "current-status.md"
    generated = "\n".join(
        [
            "# Local Runtime",
            "",
            f"- `repo_root`: `{repo_root}`",
            f"- `mcp_server_name`: `{mcp_server_name}`",
            "- `preferred_language`: `zh-CN`",
            "- `docs`:",
            f"  - `{handoff}`",
            f"  - `{current_status}`",
            "",
            "## Guidance",
            "",
            "- 图谱/不变式/自描述优先走 MCP",
            "- 代码、文档、测试直接以 `repo_root` 为工作根",
            "- 不要从 `~` 做全盘搜索",
            "",
        ]
    )
    template_text = template_text.strip()
    if not template_text:
        return generated
    return f"{generated}\n---\n{template_text}\n"


def _render_local_runtime_json(
    repo_root: Path,
    *,
    mcp_server_name: str,
) -> dict:
    return {
        "repo_root": str(repo_root),
        "mcp_server_name": mcp_server_name,
        "preferred_language": "zh-CN",
        "handoff_path": str(repo_root / "docs" / "HANDOFF.md"),
        "current_status_path": str(
            repo_root / "docs" / "superpowers" / "state" / "current-status.md"
        ),
    }


def _validate_local_runtime_files(skill_dir: Path) -> tuple[list[str], list[str]]:
    invalid: list[str] = []
    warnings: list[str] = []
    runtime_md_path = skill_dir / "references" / "local-runtime.md"
    runtime_json_path = skill_dir / "references" / "local-runtime.json"
    if not runtime_md_path.exists() or not runtime_json_path.exists():
        return invalid, warnings

    try:
        runtime_text = runtime_md_path.read_text(encoding="utf-8")
    except OSError as exc:
        invalid.append(f"references/local-runtime.md unreadable: {exc}")
        runtime_text = ""

    try:
        runtime = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        invalid.append(f"references/local-runtime.json invalid: {exc}")
        return invalid, warnings

    required_fields = [
        "repo_root",
        "mcp_server_name",
        "preferred_language",
        "handoff_path",
        "current_status_path",
    ]
    for field in required_fields:
        value = runtime.get(field)
        if not isinstance(value, str) or not value.strip():
            invalid.append(f"references/local-runtime.json missing field: {field}")

    if invalid:
        return invalid, warnings

    repo_root = Path(runtime["repo_root"]).expanduser()
    handoff_path = Path(runtime["handoff_path"]).expanduser()
    current_status_path = Path(runtime["current_status_path"]).expanduser()

    if runtime["preferred_language"] != "zh-CN":
        invalid.append("references/local-runtime.json invalid preferred_language")
    if not repo_root.exists():
        invalid.append(f"references/local-runtime.json repo_root missing: {repo_root}")
    if not handoff_path.exists():
        invalid.append(f"references/local-runtime.json handoff_path missing: {handoff_path}")
    if not current_status_path.exists():
        invalid.append(
            "references/local-runtime.json current_status_path missing: "
            f"{current_status_path}"
        )
    if str(repo_root) not in runtime_text:
        warnings.append("references/local-runtime.md missing repo_root")
    if runtime["mcp_server_name"] not in runtime_text:
        warnings.append("references/local-runtime.md missing mcp_server_name")

    return invalid, warnings


def validate_codex_skill_tree(
    skill_dir: Path,
    *,
    require_local_runtime: bool = False,
) -> dict:
    missing: list[str] = []
    for rel in REQUIRED_SOURCE_FILES:
        if not (skill_dir / rel).exists():
            missing.append(rel)

    if require_local_runtime:
        for rel in GENERATED_LOCAL_RUNTIME_FILES:
            if not (skill_dir / rel).exists():
                missing.append(rel)

    invalid: list[str] = []
    warnings: list[str] = []
    if require_local_runtime and not missing:
        invalid, warnings = _validate_local_runtime_files(skill_dir)

    return {
        "ok": not missing and not invalid,
        "skill_dir": str(skill_dir),
        "missing": missing,
        "invalid": invalid,
        "warnings": warnings,
    }


def codex_config_has_mcp_server(config_path: Path, server_name: str) -> bool:
    if not config_path.exists():
        return False
    text = config_path.read_text(encoding="utf-8")
    try:
        config = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        config = None

    if isinstance(config, dict):
        mcp_servers = config.get("mcp_servers")
        if isinstance(mcp_servers, dict) and server_name in mcp_servers:
            return True

    needles = [
        f"[mcp_servers.{server_name}]",
        f'[mcp_servers."{server_name}"]',
        f'"{server_name}" = {{',
        f'"{server_name}": {{',
    ]
    if any(needle in text for needle in needles):
        return True
    return f'"mcpServers"' in text and f'"{server_name}"' in text


def _toml_quote(value: Path | str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def build_codex_mcp_server_block(
    *,
    server_name: str,
    python_bin: Path,
    repo_root: Path,
    data_root: Path,
) -> str:
    repo_root = Path(repo_root).expanduser().resolve()
    python_bin = Path(python_bin).expanduser()
    data_root = Path(data_root).expanduser()
    mcp_script = repo_root / "scripts" / "mcp_server.py"
    args = [
        _toml_quote(mcp_script),
        _toml_quote("--root"),
        _toml_quote(data_root),
    ]
    return "\n".join(
        [
            f"{MANAGED_MCP_BLOCK_PREFIX} {server_name}",
            f"[mcp_servers.{server_name}]",
            f"command = {_toml_quote(python_bin)}",
            f"args = [{', '.join(args)}]",
            f"{MANAGED_MCP_BLOCK_SUFFIX} {server_name}",
            "",
        ]
    )


def _managed_mcp_block_pattern(server_name: str) -> re.Pattern[str]:
    escaped = re.escape(server_name)
    return re.compile(
        rf"(?ms)^# BEGIN we-together managed MCP server: {escaped}\n"
        rf".*?"
        rf"^# END we-together managed MCP server: {escaped}\n?",
    )


def _unmanaged_mcp_block_pattern(server_name: str) -> re.Pattern[str]:
    escaped = re.escape(server_name)
    return re.compile(
        rf"(?ms)^(\[mcp_servers\.{escaped}\]\n.*?)(?=^\[|\Z)",
    )


def upsert_codex_mcp_server_config(
    config_path: Path,
    *,
    server_name: str = DEFAULT_MCP_SERVER_NAME,
    python_bin: Path,
    repo_root: Path,
    data_root: Path,
    force_mcp: bool = False,
) -> dict:
    config_path = Path(config_path).expanduser().resolve()
    block = build_codex_mcp_server_block(
        server_name=server_name,
        python_bin=python_bin,
        repo_root=repo_root,
        data_root=data_root,
    )
    original = ""
    if config_path.exists():
        original = config_path.read_text(encoding="utf-8")

    managed_pattern = _managed_mcp_block_pattern(server_name)
    if managed_pattern.search(original):
        updated = managed_pattern.sub(block.rstrip("\n") + "\n", original)
        action = "replaced"
    else:
        unmanaged_pattern = _unmanaged_mcp_block_pattern(server_name)
        if unmanaged_pattern.search(original):
            if not force_mcp:
                return {
                    "ok": False,
                    "action": "conflict",
                    "config_path": str(config_path),
                    "mcp_server_name": server_name,
                    "message": (
                        "existing unmanaged MCP server config found; rerun with "
                        "force_mcp=True or --force-mcp to replace it"
                    ),
                }
            updated = unmanaged_pattern.sub(block.rstrip("\n") + "\n", original)
            action = "replaced_unmanaged"
        else:
            separator = "\n" if original and not original.endswith("\n") else ""
            prefix = "\n" if original.strip() else ""
            updated = f"{original}{separator}{prefix}{block}"
            action = "inserted"

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(updated, encoding="utf-8")
    return {
        "ok": True,
        "action": action,
        "config_path": str(config_path),
        "mcp_server_name": server_name,
        "python_bin": str(Path(python_bin).expanduser()),
        "repo_root": str(Path(repo_root).expanduser().resolve()),
        "data_root": str(Path(data_root).expanduser()),
    }


def install_codex_skill(
    source_dir: Path,
    target_dir: Path,
    *,
    repo_root: Path,
    mcp_server_name: str = DEFAULT_MCP_SERVER_NAME,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    source_check = validate_codex_skill_tree(source_dir)
    if not source_check["ok"]:
        raise FileNotFoundError(
            f"source skill layout incomplete: {source_check['missing']}"
        )

    handoff = repo_root / "docs" / "HANDOFF.md"
    current_status = repo_root / "docs" / "superpowers" / "state" / "current-status.md"
    repo_docs_missing = [
        str(path)
        for path in [repo_root, handoff, current_status]
        if not path.exists()
    ]
    if repo_docs_missing:
        raise FileNotFoundError(
            f"repo runtime references missing: {repo_docs_missing}"
        )

    if dry_run:
        return {
            "ok": True,
            "source_dir": str(source_dir),
            "target_dir": str(target_dir),
            "repo_root": str(repo_root),
            "mcp_server_name": mcp_server_name,
            "dry_run": True,
            "generated_runtime_files": GENERATED_LOCAL_RUNTIME_FILES,
        }

    if target_dir.exists():
        if not force:
            raise FileExistsError(f"target already exists: {target_dir}")
        shutil.rmtree(target_dir)

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source_dir,
        target_dir,
        ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc"),
    )

    references_dir = target_dir / "references"
    references_dir.mkdir(parents=True, exist_ok=True)
    template_path = source_dir / "references" / "local-runtime.template.md"
    template_text = ""
    if template_path.exists():
        template_text = template_path.read_text(encoding="utf-8")

    local_runtime_md = references_dir / "local-runtime.md"
    local_runtime_json = references_dir / "local-runtime.json"
    local_runtime_md.write_text(
        _render_local_runtime_markdown(
            repo_root,
            mcp_server_name=mcp_server_name,
            template_text=template_text,
        ),
        encoding="utf-8",
    )
    local_runtime_json.write_text(
        json.dumps(
            _render_local_runtime_json(
                repo_root,
                mcp_server_name=mcp_server_name,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    installed_check = validate_codex_skill_tree(
        target_dir,
        require_local_runtime=True,
    )
    return {
        "ok": installed_check["ok"],
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "repo_root": str(repo_root),
        "mcp_server_name": mcp_server_name,
        "dry_run": False,
        "missing": installed_check["missing"],
        "invalid": installed_check["invalid"],
        "warnings": installed_check["warnings"],
    }


def install_codex_skill_family(
    repo_root: Path,
    *,
    target_root: Path | None = None,
    mcp_server_name: str = DEFAULT_MCP_SERVER_NAME,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    repo_root = Path(repo_root).resolve()
    target_root = (
        (target_root or default_codex_skill_target().parent).expanduser().resolve()
    )
    sources = discover_codex_skill_family_sources(repo_root)
    missing_sources = [
        skill_name
        for skill_name in DEFAULT_CODEX_SKILL_FAMILY
        if skill_name not in sources
    ]

    reports: list[dict] = []
    overall_ok = not missing_sources
    for skill_name, source_dir in sources.items():
        report = install_codex_skill(
            source_dir,
            target_root / skill_name,
            repo_root=repo_root,
            mcp_server_name=mcp_server_name,
            force=force,
            dry_run=dry_run,
        )
        reports.append(report)
        overall_ok = overall_ok and report["ok"]

    return {
        "ok": overall_ok,
        "repo_root": str(repo_root),
        "target_root": str(target_root),
        "mcp_server_name": mcp_server_name,
        "force": force,
        "dry_run": dry_run,
        "skills": list(sources.keys()),
        "missing_sources": missing_sources,
        "reports": reports,
    }


def validate_codex_skill_family(
    target_root: Path,
    *,
    config_path: Path,
    mcp_server_name: str = DEFAULT_MCP_SERVER_NAME,
) -> dict:
    target_root = Path(target_root).expanduser().resolve()
    reports = []
    overall_ok = True

    for skill_name in DEFAULT_CODEX_SKILL_FAMILY:
        skill_dir = target_root / skill_name
        tree_report = validate_codex_skill_tree(
            skill_dir,
            require_local_runtime=True,
        )
        config_ok = codex_config_has_mcp_server(config_path, mcp_server_name)
        report = {
            "skill_name": skill_name,
            "skill_dir": str(skill_dir),
            "tree": tree_report,
            "config_path": str(config_path),
            "mcp_server_name": mcp_server_name,
            "mcp_registered": config_ok,
            "ok": tree_report["ok"] and config_ok,
        }
        reports.append(report)
        overall_ok = overall_ok and report["ok"]

    return {
        "ok": overall_ok,
        "target_root": str(target_root),
        "config_path": str(config_path),
        "mcp_server_name": mcp_server_name,
        "skills": list(DEFAULT_CODEX_SKILL_FAMILY.keys()),
        "reports": reports,
    }
