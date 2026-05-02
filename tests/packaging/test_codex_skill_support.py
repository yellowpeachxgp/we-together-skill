import json
import sys
from importlib import util
from pathlib import Path

from we_together.packaging.codex_skill_support import (
    DEFAULT_CODEX_SKILL_FAMILY,
    codex_config_has_mcp_server,
    default_codex_skill_target,
    discover_codex_skill_family_sources,
    install_codex_skill,
    install_codex_skill_family,
    validate_codex_skill_family,
    validate_codex_skill_tree,
)


def _load_validate_codex_skill():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "validate_codex_skill.py"
    module_name = "validate_codex_skill_test_module"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = util.spec_from_file_location(module_name, script_path)
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_install_codex_skill():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "install_codex_skill.py"
    module_name = "install_codex_skill_test_module"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = util.spec_from_file_location(module_name, script_path)
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_update_codex_skill():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "update_codex_skill.py"
    module_name = "update_codex_skill_test_module"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = util.spec_from_file_location(module_name, script_path)
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _make_source_skill(tmp_path: Path) -> Path:
    root = tmp_path / "codex_skill"
    (root / "agents").mkdir(parents=True)
    (root / "prompts").mkdir(parents=True)
    (root / "references").mkdir(parents=True)

    (root / "SKILL.md").write_text(
        "---\nname: we-together\ndescription: demo\n---\n",
        encoding="utf-8",
    )
    (root / "agents" / "openai.yaml").write_text(
        "interface:\n  display_name: demo\n",
        encoding="utf-8",
    )
    for name in ["dev.md", "runtime.md", "ingest.md"]:
        (root / "prompts" / name).write_text("# x\n", encoding="utf-8")
    (root / "references" / "triggers.md").write_text("# triggers\n", encoding="utf-8")
    (root / "references" / "intent-examples.md").write_text(
        "## Positive\n- we-together\n\n## Negative\n- other\n",
        encoding="utf-8",
    )
    (root / "references" / "local-runtime.template.md").write_text(
        "# template\n",
        encoding="utf-8",
    )
    return root


def _make_source_skill_family(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    for skill_name, source_dir in DEFAULT_CODEX_SKILL_FAMILY.items():
        root = repo_root / source_dir
        (root / "agents").mkdir(parents=True)
        (root / "prompts").mkdir(parents=True)
        (root / "references").mkdir(parents=True)
        (root / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: demo\n---\n",
            encoding="utf-8",
        )
        (root / "agents" / "openai.yaml").write_text(
            "interface:\n  display_name: demo\n",
            encoding="utf-8",
        )
        for prompt_name in ["dev.md", "runtime.md", "ingest.md"]:
            (root / "prompts" / prompt_name).write_text("# x\n", encoding="utf-8")
        (root / "references" / "triggers.md").write_text(
            "# triggers\n",
            encoding="utf-8",
        )
        (root / "references" / "intent-examples.md").write_text(
            "## Positive\n- we-together\n\n## Negative\n- other\n",
            encoding="utf-8",
        )
        (root / "references" / "local-runtime.template.md").write_text(
            "# template\n",
            encoding="utf-8",
        )

    (repo_root / "docs" / "superpowers" / "state").mkdir(parents=True)
    (repo_root / "docs" / "HANDOFF.md").write_text("# handoff\n", encoding="utf-8")
    (repo_root / "docs" / "superpowers" / "state" / "current-status.md").write_text(
        "# state\n",
        encoding="utf-8",
    )
    return repo_root


def test_default_codex_skill_target_uses_home(tmp_path):
    target = default_codex_skill_target(home=tmp_path)
    assert target == tmp_path / ".codex" / "skills" / "we-together"


def test_validate_codex_skill_tree_source_layout(tmp_path):
    skill_dir = _make_source_skill(tmp_path)
    report = validate_codex_skill_tree(skill_dir)
    assert report["ok"] is True
    assert report["missing"] == []


def test_validate_codex_skill_tree_installed_requires_local_runtime(tmp_path):
    skill_dir = _make_source_skill(tmp_path)
    report = validate_codex_skill_tree(skill_dir, require_local_runtime=True)
    assert report["ok"] is False
    assert "references/local-runtime.md" in report["missing"]
    assert "references/local-runtime.json" in report["missing"]


def test_install_codex_skill_copies_and_writes_runtime_refs(tmp_path):
    source_dir = _make_source_skill(tmp_path)
    repo_root = tmp_path / "repo"
    (repo_root / "docs" / "superpowers" / "state").mkdir(parents=True)
    (repo_root / "docs" / "HANDOFF.md").write_text("# handoff\n", encoding="utf-8")
    (repo_root / "docs" / "superpowers" / "state" / "current-status.md").write_text(
        "# state\n",
        encoding="utf-8",
    )

    target_dir = tmp_path / "installed"
    report = install_codex_skill(
        source_dir,
        target_dir,
        repo_root=repo_root,
    )
    assert report["ok"] is True
    assert (target_dir / "SKILL.md").exists()

    runtime_md = (target_dir / "references" / "local-runtime.md").read_text(
        encoding="utf-8"
    )
    assert str(repo_root) in runtime_md
    assert "we-together-local-validate" in runtime_md

    runtime_json = json.loads(
        (target_dir / "references" / "local-runtime.json").read_text(encoding="utf-8")
    )
    assert runtime_json["repo_root"] == str(repo_root)
    assert runtime_json["mcp_server_name"] == "we-together-local-validate"


def test_codex_config_has_mcp_server(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text(
        '[mcp_servers.we-together-local-validate]\ncommand = "python"\n',
        encoding="utf-8",
    )
    assert codex_config_has_mcp_server(config, "we-together-local-validate") is True
    assert codex_config_has_mcp_server(config, "missing-server") is False


def test_discover_codex_skill_family_sources(tmp_path):
    repo_root = _make_source_skill_family(tmp_path)
    family = discover_codex_skill_family_sources(repo_root)
    assert set(family) == set(DEFAULT_CODEX_SKILL_FAMILY)


def test_install_codex_skill_family_dry_run(tmp_path):
    repo_root = _make_source_skill_family(tmp_path)
    target_root = tmp_path / ".codex" / "skills"
    report = install_codex_skill_family(
        repo_root,
        target_root=target_root,
        dry_run=True,
    )
    assert report["ok"] is True
    assert set(report["skills"]) == set(DEFAULT_CODEX_SKILL_FAMILY)
    assert len(report["reports"]) == len(DEFAULT_CODEX_SKILL_FAMILY)


def test_validate_codex_skill_family_reports_all_installed_skills(tmp_path):
    repo_root = _make_source_skill_family(tmp_path)
    target_root = tmp_path / ".codex" / "skills"
    install_codex_skill_family(repo_root, target_root=target_root, dry_run=False)

    config = tmp_path / "config.toml"
    config.write_text(
        '[mcp_servers.we-together-local-validate]\ncommand = "python3"\n',
        encoding="utf-8",
    )

    report = validate_codex_skill_family(
        target_root,
        config_path=config,
        mcp_server_name="we-together-local-validate",
    )
    assert report["ok"] is True
    assert set(report["skills"]) == set(DEFAULT_CODEX_SKILL_FAMILY)
    assert len(report["reports"]) == len(DEFAULT_CODEX_SKILL_FAMILY)


def test_install_codex_skill_cli_dry_run_reports_install_shape(
    tmp_path, monkeypatch, capsys
):
    install_codex_skill_script = _load_install_codex_skill()
    source_dir = _make_source_skill(tmp_path)
    repo_root = tmp_path / "repo"
    (repo_root / "docs" / "superpowers" / "state").mkdir(parents=True)
    (repo_root / "docs" / "HANDOFF.md").write_text("# handoff\n", encoding="utf-8")
    (repo_root / "docs" / "superpowers" / "state" / "current-status.md").write_text(
        "# state\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "install_codex_skill.py",
            "--repo-root",
            str(repo_root),
            "--source-dir",
            str(source_dir),
            "--dry-run",
        ],
    )

    assert install_codex_skill_script.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert report["action"] == "install_codex_skill"
    assert report["mode"] == "dry-run"
    assert report["skill_name"] == "we-together"
    assert "references/local-runtime.md" in report["generated_runtime_files"]
    assert "references/local-runtime.json" in report["generated_runtime_files"]


def test_install_codex_skill_cli_family_dry_run_reports_all_skills(
    tmp_path, monkeypatch, capsys
):
    install_codex_skill_script = _load_install_codex_skill()
    repo_root = _make_source_skill_family(tmp_path)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "install_codex_skill.py",
            "--repo-root",
            str(repo_root),
            "--family",
            "--dry-run",
            "--target-dir",
            str(tmp_path / "skills"),
        ],
    )

    assert install_codex_skill_script.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert report["action"] == "install_codex_skill_family"
    assert set(report["skills"]) == set(DEFAULT_CODEX_SKILL_FAMILY)
    assert report["missing_sources"] == []
    assert len(report["reports"]) == len(DEFAULT_CODEX_SKILL_FAMILY)


def test_update_codex_skill_cli_invokes_force_install(monkeypatch):
    update_codex_skill_script = _load_update_codex_skill()
    called = {}

    class _Result:
        returncode = 0

    def _fake_run(cmd, check):
        called["cmd"] = cmd
        called["check"] = check
        return _Result()

    monkeypatch.setattr("subprocess.run", _fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "update_codex_skill.py",
            "--repo-root",
            "/tmp/repo",
            "--dry-run",
        ],
    )

    assert update_codex_skill_script.main() == 0
    assert called["check"] is False
    assert "--force" in called["cmd"]
    assert "--dry-run" in called["cmd"]
    repo_root_index = called["cmd"].index("--repo-root") + 1
    assert called["cmd"][repo_root_index].endswith("/tmp/repo")


def test_validate_codex_skill_cli_reports_source_install_and_config_states(
    tmp_path, monkeypatch, capsys
):
    validate_codex_skill = _load_validate_codex_skill()
    skill_dir = _make_source_skill(tmp_path)
    config_path = tmp_path / "config.toml"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_codex_skill.py",
            "--repo-root",
            str(tmp_path),
            "--skill-dir",
            str(skill_dir),
            "--config-path",
            str(config_path),
        ],
    )

    assert validate_codex_skill.main() == 0

    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert report["source"]["ok"] is True
    assert report["source"]["missing"] == []
    assert report["install"]["checked"] is False
    assert report["install"]["ok"] is None
    assert report["config"]["checked"] is False
    assert report["config"]["ok"] is None


def test_validate_codex_skill_cli_requires_install_and_config_when_installed(
    tmp_path, monkeypatch, capsys
):
    validate_codex_skill = _load_validate_codex_skill()
    skill_dir = _make_source_skill(tmp_path)
    config_path = tmp_path / "config.toml"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_codex_skill.py",
            "--repo-root",
            str(tmp_path),
            "--skill-dir",
            str(skill_dir),
            "--installed",
            "--config-path",
            str(config_path),
        ],
    )

    assert validate_codex_skill.main() == 1

    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is False
    assert report["source"]["ok"] is True
    assert report["install"]["checked"] is True
    assert report["install"]["ok"] is False
    assert "references/local-runtime.md" in report["install"]["missing"]
    assert "references/local-runtime.json" in report["install"]["missing"]
    assert report["config"]["checked"] is True
    assert report["config"]["ok"] is False
    assert report["config"]["mcp_server_name"] == "we-together-local-validate"


def test_validate_codex_skill_cli_installed_ok_with_runtime_refs_and_config(
    tmp_path, monkeypatch, capsys
):
    validate_codex_skill = _load_validate_codex_skill()
    source_dir = _make_source_skill(tmp_path)
    repo_root = tmp_path / "repo"
    (repo_root / "docs" / "superpowers" / "state").mkdir(parents=True)
    (repo_root / "docs" / "HANDOFF.md").write_text("# handoff\n", encoding="utf-8")
    (repo_root / "docs" / "superpowers" / "state" / "current-status.md").write_text(
        "# state\n",
        encoding="utf-8",
    )

    target_dir = tmp_path / "installed"
    install_codex_skill(source_dir, target_dir, repo_root=repo_root)

    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[mcp_servers.we-together-local-validate]\ncommand = "python3"\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_codex_skill.py",
            "--repo-root",
            str(repo_root),
            "--skill-dir",
            str(target_dir),
            "--installed",
            "--config-path",
            str(config_path),
        ],
    )

    assert validate_codex_skill.main() == 0

    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert report["source"]["ok"] is True
    assert report["install"]["checked"] is True
    assert report["install"]["ok"] is True
    assert report["install"]["missing"] == []
    assert report["config"]["checked"] is True
    assert report["config"]["ok"] is True


def test_validate_codex_skill_cli_family_installed_ok(
    tmp_path, monkeypatch, capsys
):
    validate_codex_skill = _load_validate_codex_skill()
    repo_root = _make_source_skill_family(tmp_path)
    target_root = tmp_path / "skills"
    install_codex_skill_family(repo_root, target_root=target_root, dry_run=False)

    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[mcp_servers.we-together-local-validate]\ncommand = "python3"\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_codex_skill.py",
            "--installed",
            "--family",
            "--skill-dir",
            str(target_root),
            "--config-path",
            str(config_path),
        ],
    )

    assert validate_codex_skill.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert report["action"] == "validate_codex_skill_family"
    assert len(report["reports"]) == len(DEFAULT_CODEX_SKILL_FAMILY)
