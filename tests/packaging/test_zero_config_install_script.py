from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install.sh"


def _install_script_text() -> str:
    return INSTALL_SCRIPT.read_text(encoding="utf-8")


def test_zero_config_install_script_exists_and_uses_strict_shell():
    text = _install_script_text()
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text
    assert "WE_TOGETHER_HOME" in text
    assert "WE_TOGETHER_CODEX_HOME" in text
    assert "WE_TOGETHER_REPO_URL" in text


def test_zero_config_install_script_has_required_install_stages():
    text = _install_script_text()
    required = [
        "python_version_check",
        "git_clone_or_update",
        "python3 -m venv",
        "pip install",
        '"$VENV_DIR/bin/we-together" bootstrap',
        "install_codex_skill.py",
        "--configure-mcp",
        "validate_codex_skill.py",
        "--installed",
        "--family",
    ]
    for needle in required:
        assert needle in text


def test_zero_config_install_script_supports_local_file_repo_smoke():
    text = _install_script_text()
    assert 'WE_TOGETHER_REPO_URL="${WE_TOGETHER_REPO_URL:-https://github.com/yellowpeach/we-together-skill.git}"' in text
    assert 'git clone "$WE_TOGETHER_REPO_URL" "$REPO_DIR"' in text
    assert 'WE_TOGETHER_INSTALL_MODE="${WE_TOGETHER_INSTALL_MODE:-editable}"' in text


def test_zero_config_install_script_does_not_install_system_package_managers():
    text = _install_script_text()
    forbidden = [
        "brew install",
        "apt-get install",
        "sudo ",
        "curl | bash",
    ]
    for needle in forbidden:
        assert needle not in text
