from __future__ import annotations

import re
import subprocess
import sys
from importlib import util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_release_prep():
    script_path = REPO_ROOT / "scripts" / "release_prep.py"
    module_name = "release_prep_test_module"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = util.spec_from_file_location(module_name, script_path)
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _self_audit_counts() -> dict[str, str]:
    # The test intentionally checks docs against the executable self-audit output
    # rather than hard-coding the counts here.
    proc = subprocess.run(
        [sys.executable, "scripts/self_audit.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    import json

    report = json.loads(proc.stdout)
    return {
        "version": str(report["version"]),
        "adrs": str(report["adrs_total"]),
        "invariants": str(report["invariants_total"]),
        "migrations": str(report["migrations_total"]),
        "services": str(report["services_total"]),
        "scripts": str(report["scripts_total"]),
    }


def test_reader_entrypoints_match_self_audit_counts():
    counts = _self_audit_counts()
    docs = {
        "README.md": REPO_ROOT / "README.md",
        "docs/index.md": REPO_ROOT / "docs" / "index.md",
        "docs/architecture/overview.md": REPO_ROOT / "docs" / "architecture" / "overview.md",
    }

    for label, path in docs.items():
        text = path.read_text(encoding="utf-8")
        assert counts["version"] in text, label
        assert re.search(rf"\b{counts['adrs']}\b", text), label
        assert re.search(rf"\b{counts['invariants']}\b", text), label
        assert re.search(rf"\b{counts['migrations']}\b", text), label
        assert re.search(rf"\b{counts['services']}\b", text), label
        assert re.search(rf"\b{counts['scripts']}\b", text), label


def test_gitignore_blocks_local_and_build_artifacts_from_open_source_release():
    ignored = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    required_patterns = {
        ".DS_Store",
        "dist/",
        "build/",
        "*.egg-info/",
        "db/*.sqlite3",
        "db/*.sqlite3-shm",
        "db/*.sqlite3-wal",
        ".playwright-cli/",
        "webui/node_modules/",
        "webui/dist/",
        "output/",
        ".serena/",
    }

    missing = sorted(required_patterns - set(ignored))
    assert missing == []


def test_release_prep_points_to_current_strict_gate_and_open_source_checks():
    release_prep = _load_release_prep()
    report = release_prep.run_checks("0.0.0", REPO_ROOT)
    next_steps = "\n".join(report["next"])
    check_names = {check["check"] for check in report["checks"]}

    assert "scripts/release_strict_e2e.py --profile strict" in next_steps
    assert "npm test -- --run" in next_steps
    assert "npm run build" in next_steps
    assert "npm run visual:check" in next_steps
    assert "git diff --check" in next_steps
    assert "twine check dist/*" not in next_steps
    assert "git repository root" in check_names
    assert "tracked generated artifacts" in check_names
    assert "LICENSE file" in check_names
    assert "LICENSE tracked" in check_names
    assert "pyproject.toml package name" in check_names
    assert "git tag points at HEAD" in check_names


def test_license_file_exists_for_declared_mit_license():
    license_file = REPO_ROOT / "LICENSE"
    assert license_file.exists()
    text = license_file.read_text(encoding="utf-8")
    assert "MIT License" in text
    assert "Permission is hereby granted" in text

    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'license = "MIT"' in pyproject
    assert "License :: OSI Approved :: MIT License" not in pyproject


def test_publish_docs_use_actual_distribution_name_and_safe_artifacts():
    publish = (REPO_ROOT / "docs" / "publish.md").read_text(encoding="utf-8")
    template = (REPO_ROOT / "docs" / "release_notes_template.md").read_text(encoding="utf-8")

    combined = publish + "\n" + template
    assert "we-together-skill" not in combined
    assert "we_together_skill" not in combined
    assert "we-together==X.Y.Z" in combined
    assert "dist/we_together-X.Y.Z-py3-none-any.whl" in combined
    assert "twine upload dist/*" not in combined


def test_current_release_materials_do_not_use_dist_globs_for_upload_or_check():
    current_release_files = [
        REPO_ROOT / "docs" / "release" / "pypi_checklist.md",
        REPO_ROOT / "docs" / "superpowers" / "specs" / "2026-05-03-final-product-completion-standard.md",
        REPO_ROOT / "scripts" / "build_wheel.sh",
    ]

    combined = "\n".join(path.read_text(encoding="utf-8") for path in current_release_files)
    assert "twine check dist/*" not in combined
    assert "twine upload dist/*" not in combined


def test_publish_workflow_is_manual_and_runs_gates_before_upload():
    workflow = (REPO_ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "tags:" not in workflow
    assert "python -m pytest -q" in workflow
    assert "scripts/release_strict_e2e.py --profile strict" in workflow
    assert "python -m twine check" in workflow
    assert "twine upload dist/*" not in workflow


def test_external_docs_do_not_ship_stale_commands_or_placeholder_urls():
    faq = (REPO_ROOT / "docs" / "FAQ.md").read_text(encoding="utf-8")
    codex = (REPO_ROOT / "docs" / "hosts" / "codex.md").read_text(encoding="utf-8")
    claude_submission = (REPO_ROOT / "docs" / "release" / "claude_skills_submission.md").read_text(encoding="utf-8")

    assert 'scripts/import_narration.py --root <root> --source-name "manual" --text "..."' in faq
    assert "env -u CODEX_API_KEY codex" not in codex
    assert "github.com/example" not in claude_submission
    assert "example.com" not in claude_submission


def test_public_docs_use_post_v019_cockpit_slice_until_version_bump():
    handoff = (REPO_ROOT / "docs" / "HANDOFF.md").read_text(encoding="utf-8")
    current = (REPO_ROOT / "docs" / "superpowers" / "state" / "current-status.md").read_text(encoding="utf-8")

    assert "v0.20 local cockpit" not in handoff
    assert "v0.20 local cockpit" not in current
    assert "post-v0.19 local cockpit" in handoff
    assert "post-v0.19 local cockpit" in current


def test_release_notes_distinguish_historical_entries_from_current_code_truth():
    changelog = (REPO_ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
    v018 = (REPO_ROOT / "docs" / "release_notes_v0.18.0.md").read_text(encoding="utf-8")
    v019 = (REPO_ROOT / "docs" / "release_notes_v0.19.0.md").read_text(encoding="utf-8")
    v020 = (REPO_ROOT / "docs" / "release_notes_v0.20.0.md").read_text(encoding="utf-8")

    assert "## v0.18.0" in changelog
    assert "## v0.20.0" in changelog
    assert "当前代码注册表为 28 条不变式" in v018
    assert "#29/#30" in v018 and "治理检查" in v018
    assert "docs/superpowers/state/current-status.md" in v019
    assert "853 passed, 4 skipped" in v019
    assert "zero-config installer" in v020
    assert "863 passed, 4 skipped" in v020


def test_readme_is_current_product_entrypoint_not_archived_phase_log():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Skill-first" in readme
    assert "5 分钟" in readme
    assert "WebUI" in readme
    assert "Codex native skill" in readme
    assert "release_strict_e2e.py --profile strict" in readme
    assert "122 passed" not in readme
    assert "当前仓库重点是文档和设计基线" not in readme
    assert "第一阶段路线图" not in readme
    assert "不要误解为" not in readme


def test_user_facing_docs_use_current_install_and_cli_commands():
    current_user_docs = [
        REPO_ROOT / "docs" / "getting-started.md",
        REPO_ROOT / "docs" / "hosts" / "codex.md",
        REPO_ROOT / "docs" / "tutorials" / "family_graph.md",
        REPO_ROOT / "docs" / "onboarding.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in current_user_docs)

    assert "git clone <repo>" not in combined
    assert "pip install we-together-skill" not in combined
    assert "https://github.com/yellowpeachxgp/we-together-skill" in combined

    family = (REPO_ROOT / "docs" / "tutorials" / "family_graph.md").read_text(encoding="utf-8")
    assert "--summary" in family
    assert "--participant" in family
    assert "--participants" not in family
    assert "--source-name" in family
    assert "import_narration.py --scene" not in family
    assert "chat.py --root . --scene-id" in family
