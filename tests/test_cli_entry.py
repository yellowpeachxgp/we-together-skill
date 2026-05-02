from we_together import __version__
from we_together.cli import VERSION, main


def test_version_command(capsys):
    code = main(["version"])
    captured = capsys.readouterr()
    assert code == 0
    assert VERSION in captured.out


def test_usage_prints_subcommands(capsys):
    code = main([])
    captured = capsys.readouterr()
    assert code == 0
    assert "subcommands:" in captured.out
    assert "bootstrap" in captured.out
    assert "timeline" in captured.out
    assert "what-if" in captured.out


def test_unknown_subcommand_errors(capsys):
    code = main(["nonexistent_subcmd"])
    captured = capsys.readouterr()
    assert code == 2
    assert "unknown subcommand" in captured.err


def test_exported_version_matches_cli_version():
    assert __version__ == VERSION
