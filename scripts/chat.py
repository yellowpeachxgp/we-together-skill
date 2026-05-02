"""多人共演 REPL CLI。

用法:
  .venv/bin/python scripts/chat.py --root . --scene-id <sid>
  # 默认 provider=mock（会自动用固定回答），便于冒烟；生产切到 anthropic/openai_compat

交互命令:
  /who        列出当前 scene 参与者
  /pkg        打印当前 retrieval_package 摘要
  /switch X   切换 scene
  /exit       退出
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.llm import get_llm_client
from we_together.runtime.sqlite_retrieval import (
    build_runtime_retrieval_package_from_db,
)
from we_together.services.chat_service import run_turn
from we_together.services.tenant_router import resolve_tenant_root


def _print_who(db_path: Path, scene_id: str):
    pkg = build_runtime_retrieval_package_from_db(
        db_path=db_path, scene_id=scene_id,
    )
    print("参与者:")
    for p in pkg.get("participants", []):
        print(f"  - {p['display_name']} ({p['person_id']}) [{p.get('speak_eligibility')}]")
    print("激活图:")
    for item in pkg.get("activation_map", []):
        print(f"  - {item['person_id']} {item['activation_state']} {item['activation_score']:.2f}")


def _print_pkg(db_path: Path, scene_id: str):
    pkg = build_runtime_retrieval_package_from_db(
        db_path=db_path, scene_id=scene_id,
    )
    print(json.dumps(pkg, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="多人共演 REPL")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--provider", default=None, help="LLM provider: mock/anthropic/openai_compat")
    parser.add_argument("--adapter", default="claude", choices=["claude", "openai", "openai_compat"])
    args = parser.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    llm_client = get_llm_client(args.provider)
    scene_id = args.scene_id
    history: list[dict] = []

    print(f"🗿 we together REPL | scene={scene_id} | adapter={args.adapter} | provider={llm_client.provider}")
    print("输入 /help 查看命令")

    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        if line == "/exit":
            return
        if line == "/help":
            print("/who /pkg /switch <id> /exit")
            continue
        if line == "/who":
            _print_who(db_path, scene_id)
            continue
        if line == "/pkg":
            _print_pkg(db_path, scene_id)
            continue
        if line.startswith("/switch "):
            scene_id = line.split(" ", 1)[1].strip()
            history = []
            print(f"切换到 {scene_id}")
            continue

        try:
            result = run_turn(
                db_path=db_path,
                scene_id=scene_id,
                user_input=line,
                llm_client=llm_client,
                adapter_name=args.adapter,
                history=history,
            )
        except ValueError as exc:
            print(f"!! {exc}", file=sys.stderr)
            continue

        text = result["response"]["text"]
        speaker = result["response"]["speaker_person_id"] or "skill"
        print(f"{speaker}> {text}")
        history.append({"role": "user", "content": line})
        history.append({"role": "assistant", "content": text})


if __name__ == "__main__":
    main()
