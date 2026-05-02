"""日常维护编排：一次跑完图谱自演化与清理。

步骤:
  1. relation drift
  2. state decay
  3. branch auto resolve
  4. merge_duplicates (identity 合并)
  5. persona drift (LLM)
  6. memory condense (LLM)
  7. memory_recall (anniversary) [Phase 15]
  8. cache warmup [Phase 12]
  9. graph_summary 打印
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.services.branch_resolver_service import auto_resolve_branches
from we_together.services.cache_warmer import warm_retrieval_cache
from we_together.services.identity_fusion_service import find_and_merge_duplicates
from we_together.services.memory_condenser_service import condense_memory_clusters
from we_together.services.memory_recall_service import recall_anniversary_memories
from we_together.services.persona_drift_service import drift_personas
from we_together.services.relation_drift_service import drift_relations
from we_together.services.state_decay_service import decay_states
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    parser = argparse.ArgumentParser(description="每日维护编排")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--drift-window-days", type=int, default=30)
    parser.add_argument("--decay-threshold", type=float, default=0.1)
    parser.add_argument("--branch-threshold", type=float, default=0.8)
    parser.add_argument("--branch-margin", type=float, default=0.2)
    parser.add_argument("--merge-threshold", type=float, default=0.7)
    parser.add_argument("--skip-llm", action="store_true", help="跳过 persona drift / condense")
    parser.add_argument("--skip-warm", action="store_true", help="跳过 retrieval cache 预热")
    args = parser.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    report = {
        "drift": drift_relations(db_path, window_days=args.drift_window_days),
        "decay": decay_states(db_path, threshold=args.decay_threshold),
        "auto_resolve": auto_resolve_branches(
            db_path, threshold=args.branch_threshold, margin=args.branch_margin,
        ),
        "merge_duplicates": find_and_merge_duplicates(db_path, threshold=args.merge_threshold),
    }
    if not args.skip_llm:
        try:
            report["persona_drift"] = drift_personas(
                db_path, window_days=args.drift_window_days
            )
        except Exception as exc:
            report["persona_drift"] = {"error": str(exc)}
        try:
            report["memory_condense"] = condense_memory_clusters(db_path)
        except Exception as exc:
            report["memory_condense"] = {"error": str(exc)}

    try:
        report["memory_recall"] = recall_anniversary_memories(db_path)
    except Exception as exc:
        report["memory_recall"] = {"error": str(exc)}

    if not args.skip_warm:
        try:
            report["cache_warmup"] = warm_retrieval_cache(db_path)
        except Exception as exc:
            report["cache_warmup"] = {"error": str(exc)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
