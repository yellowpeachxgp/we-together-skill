from __future__ import annotations


def test_cli_exposes_webui_host_and_webui_launcher():
    from we_together.cli import SCRIPT_MAP

    assert SCRIPT_MAP["webui-host"] == "webui_host.py"
    assert SCRIPT_MAP["webui"] == "webui_dev.py"
