from __future__ import annotations


def test_cli_exposes_webui_host_and_webui_launcher():
    from we_together.cli import SCRIPT_MAP

    assert SCRIPT_MAP["webui-host"] == "webui_host.py"
    assert SCRIPT_MAP["webui"] == "webui_dev.py"


def test_cli_exposes_common_importers_for_documented_user_paths():
    from we_together.cli import SCRIPT_MAP

    assert SCRIPT_MAP["import-narration"] == "import_narration.py"
    assert SCRIPT_MAP["import-text-chat"] == "import_text_chat.py"
    assert SCRIPT_MAP["import-email-file"] == "import_email_file.py"
    assert SCRIPT_MAP["import-file-auto"] == "import_file_auto.py"
    assert SCRIPT_MAP["import-directory"] == "import_directory.py"
    assert SCRIPT_MAP["import-auto"] == "import_auto.py"


def test_snapshot_accepts_root_after_list_subcommand(tmp_path, capsys):
    from we_together.db.bootstrap import bootstrap_project
    from scripts import snapshot

    bootstrap_project(tmp_path)
    rc = snapshot.main(["list", "--root", str(tmp_path)])

    out = capsys.readouterr().out
    assert rc == 0
    assert out.strip() == "[]"
