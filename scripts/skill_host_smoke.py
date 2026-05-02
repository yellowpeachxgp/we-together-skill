"""scripts/skill_host_smoke.py — e2e：bootstrap → seed → run_turn → dashboard smoke。

用法:
  python scripts/skill_host_smoke.py --root /tmp/smoke

输出 JSON：每步结果 + pass/fail summary。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from we_together.services.tenant_router import resolve_tenant_root


def run_smoke(root: Path) -> dict:
    results: list[dict] = []

    from we_together.db.bootstrap import bootstrap_project
    try:
        bootstrap_project(root)
        results.append({"step": "bootstrap", "ok": True})
    except Exception as exc:
        results.append({"step": "bootstrap", "ok": False, "err": str(exc)})
        return {"ok": False, "results": results}

    try:
        from seed_demo import seed_society_c
        summary = seed_society_c(root)
        results.append({
            "step": "seed_society_c", "ok": True,
            "persons": len(summary.get("persons", {})),
        })
    except Exception as exc:
        results.append({"step": "seed_society_c", "ok": False, "err": str(exc)})
        return {"ok": False, "results": results}

    try:
        from we_together.llm.providers.mock import MockLLMClient
        from we_together.services.chat_service import run_turn
        scene_id = list(summary.get("scenes", {}).values())[0] if summary.get("scenes") else None
        db = root / "db" / "main.sqlite3"
        if scene_id:
            r = run_turn(
                db_path=db, scene_id=scene_id, user_input="早上好",
                llm_client=MockLLMClient(default_content="你好，我收到了。"),
                adapter_name="openai_compat",
            )
            text = (
                r.get("response", {}).get("text")
                or r.get("text")
                or r.get("response_text", "")
            )
            results.append({
                "step": "run_turn", "ok": bool(text),
                "text": text,
            })
        else:
            results.append({"step": "run_turn", "ok": False, "err": "no scene in seed"})
    except Exception as exc:
        results.append({"step": "run_turn", "ok": False, "err": str(exc)})

    # dashboard summary
    try:
        from dashboard import _summary
        s = _summary(root)
        results.append({"step": "dashboard_summary", "ok": "error" not in s,
                        "summary": s})
    except Exception as exc:
        results.append({"step": "dashboard_summary", "ok": False, "err": str(exc)})

    overall_ok = all(r.get("ok") for r in results)
    return {"ok": overall_ok, "results": results}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--tenant-id", default=None)
    args = ap.parse_args()
    tenant_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    tenant_root.mkdir(parents=True, exist_ok=True)
    report = run_smoke(tenant_root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
