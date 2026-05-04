"""we-together 统一 CLI 入口。

用法:
  we-together <subcommand> [options]

子命令:
  bootstrap        初始化项目目录 + 迁移 + seed
  seed-demo        灌入 Society C demo 数据
  create-scene     创建一个 scene
  build-pkg        构建 runtime_retrieval_package
  dialogue-turn    一次端到端对话轮次
  snapshot         snapshot 子命令（list/rollback/replay）
  daily-maint      跑 daily_maintenance 编排
  graph-summary    打印图谱摘要
  onboard          新用户交互式引导（Phase 13）
  eval-relation    跑 relation 推理 eval（Phase 14）
  timeline         打印 person 时间线（Phase 15）
  what-if          What-if 社会模拟 teaser（Phase 17）
  webui-host      启动 WebUI 本地 skill bridge
  webui           启动 WebUI 本地开发环境（bridge + Vite）
  version          打印版本
"""
from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

VERSION = "0.20.0"

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"

# subcommand → script filename
SCRIPT_MAP = {
    "bootstrap": "bootstrap.py",
    "seed-demo": "seed_demo.py",
    "create-scene": "create_scene.py",
    "build-pkg": "build_retrieval_package.py",
    "dialogue-turn": "dialogue_turn.py",
    "snapshot": "snapshot.py",
    "daily-maint": "daily_maintenance.py",
    "graph-summary": "graph_summary.py",
    "onboard": "onboard.py",
    "eval-relation": "eval_relation.py",
    "timeline": "timeline.py",
    "relation-timeline": "relation_timeline.py",
    "what-if": "what_if.py",
    "agent-chat": "agent_chat.py",
    "package-skill": "package_skill.py",
    "branch-console": "branch_console.py",
    "metrics-server": "metrics_server.py",
    "bench-large": "bench_large.py",
    "condense-memories": "condense_memories.py",
    "cold-memory": "cold_memory.py",
    "merge-duplicates": "merge_duplicates.py",
    "record-dialogue": "record_dialogue.py",
    "extract-facets": "extract_facets.py",
    "chat": "chat.py",
    "webui-host": "webui_host.py",
    "webui": "webui_dev.py",
    # Phase 18+
    "mcp-server": "mcp_server.py",
    "import-audio": "import_audio.py",
    "simulate": "simulate.py",
}


def _usage() -> str:
    lines = ["usage: we-together <subcommand> [options]", "", "subcommands:"]
    for name in sorted(SCRIPT_MAP):
        lines.append(f"  {name}")
    lines.append("  version")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print(_usage())
        return 0
    if argv[0] in {"version", "--version", "-V"}:
        print(f"we-together {VERSION}")
        return 0

    sub = argv[0]
    if sub not in SCRIPT_MAP:
        print(f"unknown subcommand: {sub}", file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2

    script_path = SCRIPTS_DIR / SCRIPT_MAP[sub]
    if not script_path.exists():
        print(f"script not found: {script_path}", file=sys.stderr)
        return 2

    # 透传剩余参数
    sys.argv = [str(script_path)] + argv[1:]
    runpy.run_path(str(script_path), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
