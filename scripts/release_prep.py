"""scripts/release_prep.py — 发布前本地自检。

检查：
- tag 存在
- pyproject/cli VERSION 一致
- wheel 能 build
- 关键 ADR/CHANGELOG/release_notes 存在
- Git 仓库根目录与项目根目录一致，避免从父仓库发布无关文件
- build/dist/egg-info/宿主缓存等生成物未被 Git 跟踪
- 全量 pytest 可一键重跑（不真跑，只打印命令）

用法:
  python scripts/release_prep.py --version 0.19.0
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path


TRACKED_GENERATED_PATHS = [
    ".coverage",
    "coverage.json",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "build",
    "dist",
    "src/we_together.egg-info",
    "webui/dist",
    ".playwright-cli",
    ".serena",
    "output",
    "../.DS_Store",
]
EXPECTED_PACKAGE_NAME = "we-together"


def _check(name: str, ok: bool, detail: str = "") -> dict:
    return {"check": name, "ok": ok, "detail": detail}


def _git_output(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=repo_root,
        stderr=subprocess.STDOUT,
    ).decode("utf-8").strip()


def _tracked_generated_artifacts(repo_root: Path) -> list[str]:
    try:
        out = _git_output(repo_root, ["ls-files", "--", *TRACKED_GENERATED_PATHS])
    except Exception:
        return []
    return sorted(line for line in out.splitlines() if line)


def _git_tracks(repo_root: Path, rel_path: str) -> bool:
    try:
        _git_output(repo_root, ["ls-files", "--error-unmatch", rel_path])
        return True
    except Exception:
        return False


def run_checks(version: str, repo_root: Path) -> dict:
    checks: list[dict] = []
    repo_root = repo_root.resolve()

    # Git repository shape: this project must be released from its own repo root,
    # not from a parent monorepo that can accidentally include unrelated files.
    try:
        git_root = Path(_git_output(repo_root, ["rev-parse", "--show-toplevel"])).resolve()
        checks.append(_check(
            "git repository root",
            git_root == repo_root,
            f"found {git_root}, expected {repo_root}",
        ))
    except Exception as exc:
        checks.append(_check("git repository root", False, str(exc)))

    tracked_generated = _tracked_generated_artifacts(repo_root)
    checks.append(_check(
        "tracked generated artifacts",
        not tracked_generated,
        "none" if not tracked_generated else ", ".join(tracked_generated[:20]) + (
            f" ... (+{len(tracked_generated) - 20} more)" if len(tracked_generated) > 20 else ""
        ),
    ))

    # pyproject version
    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    pyproject_data = tomllib.loads(pyproject)
    package_name = str(pyproject_data.get("project", {}).get("name", ""))
    checks.append(_check(
        "pyproject.toml package name",
        package_name == EXPECTED_PACKAGE_NAME,
        f"found {package_name or 'none'}, expected {EXPECTED_PACKAGE_NAME}",
    ))
    m = re.search(r'version\s*=\s*"([^"]+)"', pyproject)
    checks.append(_check(
        "pyproject.toml version", m is not None and m.group(1) == version,
        f"found {m.group(1) if m else 'none'}, expected {version}",
    ))

    license_path = repo_root / "LICENSE"
    license_text = license_path.read_text(encoding="utf-8") if license_path.exists() else ""
    checks.append(_check(
        "LICENSE file",
        license_path.exists() and "MIT License" in license_text and "Permission is hereby granted" in license_text,
        "LICENSE exists and contains MIT grant text",
    ))
    checks.append(_check(
        "LICENSE tracked",
        _git_tracks(repo_root, "LICENSE"),
        "git ls-files --error-unmatch LICENSE",
    ))

    # cli VERSION
    cli = (repo_root / "src" / "we_together" / "cli.py").read_text(encoding="utf-8")
    m2 = re.search(r'VERSION\s*=\s*"([^"]+)"', cli)
    checks.append(_check(
        "cli.py VERSION", m2 is not None and m2.group(1) == version,
        f"found {m2.group(1) if m2 else 'none'}, expected {version}",
    ))

    # CHANGELOG has entry
    chlog = (repo_root / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
    has_entry = f"v{version}" in chlog
    checks.append(_check(
        "CHANGELOG entry", has_entry,
        f"'v{version}' in docs/CHANGELOG.md",
    ))

    # release_notes exists
    rn = repo_root / "docs" / f"release_notes_v{version}.md"
    checks.append(_check(
        "release_notes file", rn.exists(),
        str(rn.relative_to(repo_root)),
    ))

    # git tag
    try:
        out = _git_output(repo_root, ["tag", "-l", f"v{version}"])
        checks.append(_check(
            "git tag exists", out == f"v{version}", f"git tag v{version}",
        ))
    except Exception as exc:
        checks.append(_check("git tag exists", False, str(exc)))

    # build artifacts
    wheel_path = repo_root / "dist" / f"we_together-{version}-py3-none-any.whl"
    sdist_path = repo_root / "dist" / f"we_together-{version}.tar.gz"
    checks.append(_check(
        "wheel artifact", wheel_path.exists(),
        str(wheel_path.relative_to(repo_root)),
    ))
    checks.append(_check(
        "sdist artifact", sdist_path.exists(),
        str(sdist_path.relative_to(repo_root)),
    ))

    final_gate = [
        "python -m pytest -q",
        "python scripts/invariants_check.py summary",
        "python scripts/self_audit.py",
        "python scripts/release_strict_e2e.py --profile strict",
        "cd webui && npm test -- --run",
        "cd webui && npm run build",
        "cd webui && npm run visual:check",
        "git diff --check",
        f"python -m twine check {wheel_path.relative_to(repo_root)} {sdist_path.relative_to(repo_root)}",
        f"python -m twine upload --repository testpypi {wheel_path.relative_to(repo_root)} {sdist_path.relative_to(repo_root)}",
        f"python -m twine upload {wheel_path.relative_to(repo_root)} {sdist_path.relative_to(repo_root)}",
        "# 本地 TestPyPI 测试：见 docs/release/pypi_checklist.md",
    ]
    all_ok = all(c["ok"] for c in checks)
    return {
        "version": version,
        "ok": all_ok,
        "checks": checks,
        "next": final_gate if all_ok else [
            "修复上面 ok=False 的检查后重跑",
            *final_gate,
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    args = ap.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    report = run_checks(args.version, repo_root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
