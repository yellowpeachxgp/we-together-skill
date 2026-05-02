"""社交平台公共数据 importer (X/微博 JSON dump)。

输入 JSON 结构（自定义通用格式，各平台导出工具可先转为此格式）:
  {
    "platform": "x|weibo",
    "owner_handle": "...",
    "posts": [
      {"id": "...", "text": "...", "created_at": "...", "mentions": ["..."], "reposts": int, "likes": int}
    ],
    "following": [{"handle": "..."}],
    "followers": [{"handle": "..."}]
  }
"""
from __future__ import annotations

import json
from pathlib import Path


def import_social_dump(json_path: Path) -> dict:
    if not json_path.exists():
        raise FileNotFoundError(f"social dump not found: {json_path}")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    platform = data.get("platform", "social")
    owner = data.get("owner_handle", "self")

    identities: dict[str, dict] = {}
    for f in data.get("following", []) + data.get("followers", []):
        h = f.get("handle")
        if not h or h in identities:
            continue
        identities[h] = {
            "display_name": h,
            "platform": platform,
            "external_id": h,
            "confidence": 0.55,
            "source": "social_importer",
        }

    events: list[dict] = []
    for p in data.get("posts", []):
        for m in p.get("mentions", []) or []:
            if m and m not in identities:
                identities[m] = {
                    "display_name": m,
                    "platform": platform,
                    "external_id": m,
                    "confidence": 0.5,
                    "source": "social_importer",
                }
        events.append({
            "summary": p.get("text", ""),
            "event_type": "social_post",
            "timestamp": p.get("created_at"),
            "sender_external_id": owner,
            "mentions": p.get("mentions", []),
            "confidence": 0.5,
            "source": "social_importer",
            "guid": p.get("id"),
        })

    return {
        "identity_candidates": list(identities.values()),
        "event_candidates": events,
        "source": "social_importer",
        "platform": platform,
    }
