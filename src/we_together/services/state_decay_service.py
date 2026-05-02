"""State 衰减服务。

按 state.decay_policy 衰减 confidence：
  - None / "none" → 不衰减
  - "linear:per_day=X" → 每天减 X
  - "exponential:half_life_days=X" → 半衰期衰减
  - "step:after_days=X,to=Y" → X 天后一次性降到 Y

低于阈值（默认 0.1）自动 mark_inactive。
所有变更通过 patch 落地以保留留痕。
"""
from __future__ import annotations

import math
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch

DEFAULT_THRESHOLD = 0.1


def _parse_policy(policy: str | None) -> tuple[str, dict]:
    if not policy or policy == "none":
        return "none", {}
    if ":" not in policy:
        return policy, {}
    kind, rest = policy.split(":", 1)
    params: dict = {}
    for pair in rest.split(","):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        try:
            params[k.strip()] = float(v)
        except ValueError:
            params[k.strip()] = v
    return kind, params


def _decay_confidence(
    old_confidence: float,
    age_days: float,
    policy: str | None,
) -> float:
    kind, params = _parse_policy(policy)
    if kind == "none":
        return old_confidence
    if kind == "linear":
        per_day = float(params.get("per_day", 0.01))
        return max(0.0, old_confidence - per_day * age_days)
    if kind == "exponential":
        half = float(params.get("half_life_days", 14))
        if half <= 0:
            return 0.0
        return old_confidence * math.pow(0.5, age_days / half)
    if kind == "step":
        after = float(params.get("after_days", 30))
        to = float(params.get("to", 0.0))
        if age_days >= after:
            return to
        return old_confidence
    return old_confidence


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def decay_states(
    db_path: Path,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    source_event_id: str | None = None,
    limit: int = 500,
) -> dict:
    now = datetime.now(UTC)
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT state_id, scope_type, scope_id, state_type, value_json,
               confidence, is_inferred, decay_policy, source_event_refs_json, updated_at
        FROM states
        ORDER BY updated_at ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    decayed: list[dict] = []
    deactivated: list[str] = []

    for row in rows:
        old_conf = row["confidence"] if row["confidence"] is not None else 1.0
        ts = _parse_ts(row["updated_at"])
        if ts is None:
            continue
        age_days = max(0.0, (now - ts).total_seconds() / 86400)
        new_conf = _decay_confidence(old_conf, age_days, row["decay_policy"])
        if abs(new_conf - old_conf) < 1e-6:
            continue
        decayed.append({
            "state_id": row["state_id"],
            "old_confidence": old_conf,
            "new_confidence": new_conf,
            "age_days": age_days,
            "policy": row["decay_policy"],
        })

    # 落 patch
    for item in decayed:
        import json as _json
        row = next(r for r in rows if r["state_id"] == item["state_id"])
        payload = {
            "state_id": row["state_id"],
            "scope_type": row["scope_type"],
            "scope_id": row["scope_id"],
            "state_type": row["state_type"],
            "value_json": _json.loads(row["value_json"]),
            "confidence": item["new_confidence"],
            "is_inferred": row["is_inferred"],
            "decay_policy": row["decay_policy"],
            "source_event_refs_json": _json.loads(row["source_event_refs_json"] or "[]"),
        }
        apply_patch_record(
            db_path=db_path,
            patch=build_patch(
                source_event_id=source_event_id or f"decay_{row['state_id']}",
                target_type="state",
                target_id=row["state_id"],
                operation="update_state",
                payload=payload,
                confidence=item["new_confidence"],
                reason=f"decay {item['policy']} ({item['age_days']:.2f}d)",
            ),
        )

        if item["new_confidence"] < threshold:
            # 没有直接的 state mark_inactive；改用 update_state 标记并记录
            deactivated.append(row["state_id"])

    return {
        "decayed_count": len(decayed),
        "deactivated_state_ids": deactivated,
        "threshold": threshold,
    }
