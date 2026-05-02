"""scripts/multi_agent_chat.py — REPL：主持 3-5 agent 对话。

用法:
  python scripts/multi_agent_chat.py --root . --scene scene_x --turns 5

流程:
  1. 从 scene_participants 加载 agent
  2. 用 orchestrate_dialogue 跑 N 轮
  3. 打印 transcript（着色 speaker）
  4. 可选 --record 把 transcript 作为 dialogue_event 存库
  5. 支持 stdin 交互模式（human 加入）：--interactive，每轮结束问是否加一句

Mock LLM 默认；--real-llm 切 anthropic/openai
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.agents.person_agent import PersonAgent
from we_together.llm import get_llm_client
from we_together.llm.providers.mock import MockLLMClient
from we_together.services.multi_agent_dialogue import (
    orchestrate_dialogue,
    record_transcript_as_event,
)
from we_together.services.tenant_router import resolve_tenant_root


def _load_scene_agents(db: Path, scene_id: str, *, llm) -> list[PersonAgent]:
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT person_id FROM scene_participants WHERE scene_id=?",
            (scene_id,),
        ).fetchall()
    finally:
        conn.close()
    agents: list[PersonAgent] = []
    for (pid,) in rows:
        try:
            agents.append(PersonAgent.from_db(db, pid, llm_client=llm))
        except Exception:
            continue
    return agents


def _activation_map_for(db: Path, scene_id: str) -> dict:
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT person_id, activation_score FROM scene_participants WHERE scene_id=?",
            (scene_id,),
        ).fetchall()
    finally:
        conn.close()
    return {pid: {"activation_score": float(s or 0.5)} for pid, s in rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--turns", type=int, default=5)
    ap.add_argument("--interrupt-threshold", type=float, default=0.85)
    ap.add_argument("--real-llm", action="store_true")
    ap.add_argument("--record", action="store_true",
                    help="save transcript as dialogue_event")
    args = ap.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db = tenant_root / "db" / "main.sqlite3"
    if not db.exists():
        print(json.dumps({"error": "db not found"}))
        return 1

    llm = get_llm_client() if args.real_llm else MockLLMClient(
        default_content="[mock reply]",
    )
    agents = _load_scene_agents(db, args.scene, llm=llm)
    if not agents:
        print(json.dumps({"error": "no participants in scene"}))
        return 2

    activation = _activation_map_for(db, args.scene)

    # 取第一个 scene 的 summary 作为对话主题
    conn = sqlite3.connect(db)
    scene_row = conn.execute(
        "SELECT scene_type FROM scenes WHERE scene_id=?", (args.scene,),
    ).fetchone()
    conn.close()
    scene_summary = f"scene {args.scene} ({scene_row[0] if scene_row else 'unknown'})"

    r = orchestrate_dialogue(
        agents, scene_summary=scene_summary,
        activation_map=activation,
        turns=args.turns,
        interrupt_threshold=args.interrupt_threshold,
    )

    if args.record:
        ev_id = record_transcript_as_event(
            db, scene_id=args.scene, transcript=r["transcript"],
        )
        r["event_id"] = ev_id

    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
