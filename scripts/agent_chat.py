"""Agent loop CLI：让 chat 支持 tool_call → tool_result 循环。

当前内置工具:
  - graph_summary : 打印当前图谱摘要
  - retrieval_pkg : 打印当前 scene 的 retrieval_package

用法:
  .venv/bin/python scripts/agent_chat.py --root . --scene-id <scene_id> --input "..."
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.llm import get_llm_client
from we_together.runtime.sqlite_retrieval import build_runtime_retrieval_package_from_db
from we_together.services.agent_loop_service import run_turn_agent
from we_together.services.tenant_router import resolve_tenant_root


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--scene-id", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--max-iters", type=int, default=3)
    args = ap.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    if not db_path.exists():
        print(f"db not found: {db_path}", file=sys.stderr)
        sys.exit(2)

    def _graph_summary(payload: dict) -> str:
        pkg = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=args.scene_id)
        return json.dumps(
            {"scene_summary": pkg.get("scene_summary"),
             "participants_count": len(pkg.get("participants", [])),
             "memory_count": len(pkg.get("relevant_memories", []))},
            ensure_ascii=False,
        )

    def _retrieval_pkg(payload: dict) -> str:
        pkg = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=args.scene_id)
        return json.dumps(pkg, ensure_ascii=False)[:500]

    dispatcher = {
        "graph_summary": _graph_summary,
        "retrieval_pkg": _retrieval_pkg,
    }

    result = run_turn_agent(
        db_path=db_path, scene_id=args.scene_id, user_input=args.input,
        tool_dispatcher=dispatcher, llm_client=get_llm_client(),
        max_iters=args.max_iters,
    )
    print(json.dumps({
        "final_text": result.final_text,
        "event_ids": result.event_ids,
        "steps": [
            {"type": s.step_type, "tool": s.tool, "args": s.args,
             "result": s.result, "text": s.text}
            for s in result.steps
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
