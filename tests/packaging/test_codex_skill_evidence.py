import json
import sys
from importlib import util
from pathlib import Path

from we_together.packaging.codex_skill_evidence import (
    collect_codex_skill_evidence,
    inspect_codex_session_for_skills,
)


def _load_capture_codex_skill_evidence():
    script_path = (
        Path(__file__).resolve().parents[2] / "scripts" / "capture_codex_skill_evidence.py"
    )
    module_name = "capture_codex_skill_evidence_test_module"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = util.spec_from_file_location(module_name, script_path)
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_session(session_path: Path, records: list[dict]) -> Path:
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    return session_path


def _sample_skill_session(skill_name: str) -> list[dict]:
    base = f"/Users/demo/.codex/skills/{skill_name}"
    return [
        {
            "timestamp": "2026-04-24T21:09:56.605Z",
            "type": "event_msg",
            "payload": {
                "type": "exec_command_end",
                "parsed_cmd": [
                    {
                        "type": "read",
                        "name": "local-runtime.md",
                        "path": f"{base}/references/local-runtime.md",
                    }
                ],
            },
        },
        {
            "timestamp": "2026-04-24T21:09:56.965Z",
            "type": "event_msg",
            "payload": {
                "type": "agent_message",
                "message": "技能里要求先读本地运行时映射，我现在直接从 references/local-runtime.md 找仓库根和状态文档。",
            },
        },
        {
            "timestamp": "2026-04-24T21:10:04.458Z",
            "type": "event_msg",
            "payload": {
                "type": "exec_command_end",
                "parsed_cmd": [
                    {
                        "type": "read",
                        "name": "dev.md",
                        "path": f"{base}/prompts/dev.md",
                    }
                ],
            },
        },
    ]


def test_inspect_codex_session_for_skills_finds_runtime_prompt_and_message(tmp_path):
    session_path = _write_session(
        tmp_path / "2026" / "04" / "24" / "rollout-a.jsonl",
        _sample_skill_session("we-together"),
    )

    report = inspect_codex_session_for_skills(
        session_path,
        skill_names=["we-together"],
    )

    assert report["matched"] is True
    assert report["matched_skills"] == ["we-together"]
    evidence = report["hits_by_skill"]["we-together"]
    assert evidence["local_runtime_reads"][0]["path"].endswith("references/local-runtime.md")
    assert evidence["prompt_reads"][0]["path"].endswith("prompts/dev.md")
    assert len(evidence["messages"]) == 1


def test_collect_codex_skill_evidence_ignores_skill_mentions_without_reads(tmp_path):
    skill_session = _write_session(
        tmp_path / "2026" / "04" / "24" / "rollout-a.jsonl",
        _sample_skill_session("we-together"),
    )
    noise_session = _write_session(
        tmp_path / "2026" / "04" / "24" / "rollout-b.jsonl",
        [
            {
                "timestamp": "2026-04-24T21:02:21.434Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "developer",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "- we-together: Use when the user is asking about the project.",
                        }
                    ],
                },
            }
        ],
    )

    report = collect_codex_skill_evidence(
        tmp_path,
        skill_names=["we-together"],
    )

    assert report["ok"] is True
    assert report["scanned_sessions"] == 2
    assert report["matched_sessions"] == 1
    assert report["hits_by_skill"]["we-together"]["sessions"] == 1
    assert report["hits_by_skill"]["we-together"]["local_runtime_reads"] == 1
    assert report["hits_by_skill"]["we-together"]["prompt_reads"] == 1
    assert report["hits_by_skill"]["we-together"]["messages"] == 1
    assert report["sessions"][0]["session_path"] == str(skill_session)
    assert all(session["session_path"] != str(noise_session) for session in report["sessions"][1:])


def test_capture_codex_skill_evidence_cli_reports_summary(
    tmp_path, monkeypatch, capsys
):
    capture_script = _load_capture_codex_skill_evidence()
    _write_session(
        tmp_path / "2026" / "04" / "24" / "rollout-a.jsonl",
        _sample_skill_session("we-together-runtime"),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "capture_codex_skill_evidence.py",
            "--session-root",
            str(tmp_path),
            "--skill",
            "we-together-runtime",
        ],
    )

    assert capture_script.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert report["action"] == "capture_codex_skill_evidence"
    assert report["matched_sessions"] == 1
    assert report["hits_by_skill"]["we-together-runtime"]["prompt_reads"] == 1
