"""webhook_alert（Phase 49 UX-6/7）：基于阈值触发 webhook POST。

配置 rules = [
  {"metric": "events_per_day", "op": ">", "threshold": 1000, "url": "https://..."},
  {"metric": "integrity_issues", "op": ">", "threshold": 10, "url": "..."},
]
evaluate(metrics, rules) → 列出命中规则
dispatch(matches, dry_run) → 真 POST（或 dry_run 只返 payload）
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


OPS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


@dataclass
class AlertRule:
    metric: str
    op: str
    threshold: float
    url: str
    name: str | None = None

    def evaluate(self, value: float) -> bool:
        fn = OPS.get(self.op)
        if fn is None:
            raise ValueError(f"unknown op: {self.op}")
        return fn(value, self.threshold)


def evaluate(metrics: dict[str, Any], rules: list[AlertRule]) -> list[dict]:
    matches: list[dict] = []
    for rule in rules:
        value = metrics.get(rule.metric)
        if value is None:
            continue
        try:
            if rule.evaluate(float(value)):
                matches.append({
                    "rule_name": rule.name or f"{rule.metric}{rule.op}{rule.threshold}",
                    "metric": rule.metric,
                    "value": value,
                    "threshold": rule.threshold,
                    "op": rule.op,
                    "url": rule.url,
                })
        except (TypeError, ValueError):
            continue
    return matches


def dispatch(matches: list[dict], *, dry_run: bool = True,
             timeout: float = 3.0) -> dict:
    """发送 alert。dry_run=True 只返 payload 不真 POST。"""
    sent: list[dict] = []
    failed: list[dict] = []
    for m in matches:
        payload = {
            "rule": m["rule_name"],
            "metric": m["metric"],
            "value": m["value"],
            "threshold": m["threshold"],
            "op": m["op"],
        }
        if dry_run:
            sent.append({**m, "payload": payload, "dry_run": True})
            continue
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            m["url"], data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                sent.append({**m, "status": resp.status})
        except urllib.error.URLError as exc:
            failed.append({**m, "error": str(exc)})
        except Exception as exc:  # pragma: no cover
            failed.append({**m, "error": str(exc)})
    return {"sent": sent, "failed": failed}


def parse_rules(raw: list[dict]) -> list[AlertRule]:
    out: list[AlertRule] = []
    for r in raw:
        out.append(AlertRule(
            metric=r["metric"], op=r["op"],
            threshold=float(r["threshold"]), url=r["url"],
            name=r.get("name"),
        ))
    return out
