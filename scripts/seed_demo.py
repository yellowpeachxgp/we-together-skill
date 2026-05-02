"""Demo 小社会：8 人 × 多种关系 × 多个场景。

用法：
  .venv/bin/python scripts/seed_demo.py --root <tmp-or-root>

幂等：若已存在同名 primary_name 的 person，会复用而非重复创建。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.db.bootstrap import bootstrap_project
from we_together.services.group_service import add_group_member, create_group
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch
from we_together.services.scene_service import add_scene_participant, create_scene
from we_together.services.tenant_router import resolve_tenant_root


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_person(db_path: Path, primary_name: str,
                    persona: str | None = None,
                    style: str | None = None,
                    boundary: str | None = None) -> str:
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT person_id FROM persons WHERE primary_name = ? LIMIT 1", (primary_name,)
    ).fetchone()
    if row:
        conn.close()
        return row[0]
    pid = f"person_{uuid.uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO persons(
            person_id, primary_name, status, persona_summary, style_summary,
            boundary_summary, confidence, metadata_json, created_at, updated_at
        ) VALUES(?, ?, 'active', ?, ?, ?, 0.9, '{}', ?, ?)
        """,
        (pid, primary_name, persona, style, boundary, _now(), _now()),
    )
    conn.commit()
    conn.close()
    return pid


def _ensure_relation(db_path: Path, relation_key: str, core_type: str, summary: str,
                     strength: float = 0.7) -> str:
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT relation_id FROM relations WHERE custom_label = ? LIMIT 1", (relation_key,)
    ).fetchone()
    if row:
        conn.close()
        return row[0]
    rid = f"relation_{uuid.uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO relations(
            relation_id, core_type, custom_label, summary, directionality,
            strength, stability, visibility, status, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, ?, ?, ?, 'bidirectional', ?, 0.6, 'known', 'active', 0.8,
                 '{}', ?, ?)
        """,
        (rid, core_type, relation_key, summary, strength, _now(), _now()),
    )
    conn.commit()
    conn.close()
    return rid


def _link_event_for_relation(db_path: Path, relation_id: str, person_ids: list[str], summary: str) -> str:
    event_id = f"evt_{uuid.uuid4().hex[:14]}"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO events(
            event_id, event_type, source_type, timestamp, summary, visibility_level,
            confidence, is_structured, raw_evidence_refs_json, metadata_json, created_at
        ) VALUES(?, 'narration_seed', 'demo', ?, ?, 'visible', 0.9, 1, '[]', '{}', ?)
        """,
        (event_id, _now(), summary, _now()),
    )
    for pid in person_ids:
        conn.execute(
            "INSERT INTO event_participants(event_id, person_id, participant_role) VALUES(?, ?, 'mentioned')",
            (event_id, pid),
        )
    conn.execute(
        "INSERT INTO event_targets(event_id, target_type, target_id, impact_hint) VALUES(?, 'relation', ?, 'demo seed')",
        (event_id, relation_id),
    )
    conn.commit()
    conn.close()
    return event_id


def _ensure_memory_shared(db_path: Path, memory_id_hint: str, summary: str,
                          owner_person_ids: list[str], memory_type: str = "shared_memory") -> str:
    memory_id = f"mem_{uuid.uuid4().hex[:12]}"
    # patch 落记忆
    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id=f"seed_{memory_id_hint}",
            target_type="memory",
            target_id=memory_id,
            operation="create_memory",
            payload={
                "memory_id": memory_id,
                "memory_type": memory_type,
                "summary": summary,
                "relevance_score": 0.8,
                "confidence": 0.8,
                "is_shared": 1,
                "status": "active",
                "metadata_json": {"source": "demo_seed"},
            },
            confidence=0.8,
            reason="demo seed memory",
        ),
    )
    # 添加 owners
    conn = sqlite3.connect(db_path)
    for pid in owner_person_ids:
        conn.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) VALUES(?, 'person', ?, NULL)",
            (memory_id, pid),
        )
    conn.commit()
    conn.close()
    return memory_id


def seed_society_c(root: Path) -> dict:
    db_path = root / "db" / "main.sqlite3"
    bootstrap_project(root)

    persons = {
        "alice": _ensure_person(db_path, "Alice", "理性领导者", "简洁果断", "保护个人时间"),
        "bob": _ensure_person(db_path, "Bob", "技术极客", "直接而幽默", None),
        "carol": _ensure_person(db_path, "Carol", "温和协调者", "圆融", "避免正面冲突"),
        "dan": _ensure_person(db_path, "Dan", "安静细腻", "温柔", "需要独处空间"),
        "eve": _ensure_person(db_path, "Eve", "外向活跃", "热情", None),
        "frank": _ensure_person(db_path, "Frank", "冷静观察者", "慢节奏", None),
        "grace": _ensure_person(db_path, "Grace", "务实", "直接", None),
        "henry": _ensure_person(db_path, "Henry", "资深导师", "富有耐心", None),
    }

    group_id = create_group(db_path=db_path, group_type="team", name="CoreEng", summary="核心工程组")
    add_group_member(db_path=db_path, group_id=group_id, person_id=persons["alice"], role_label="owner")
    add_group_member(db_path=db_path, group_id=group_id, person_id=persons["bob"], role_label="member")
    add_group_member(db_path=db_path, group_id=group_id, person_id=persons["carol"], role_label="member")

    relations = {
        "alice_bob_colleague": _ensure_relation(db_path, "alice_bob_colleague", "work", "长期合作的 CEO/CTO", 0.85),
        "alice_carol_colleague": _ensure_relation(db_path, "alice_carol_colleague", "work", "CEO/PM", 0.7),
        "bob_carol_colleague": _ensure_relation(db_path, "bob_carol_colleague", "work", "CTO/PM", 0.7),
        "alice_dan_intimate": _ensure_relation(db_path, "alice_dan_intimate", "intimacy", "伴侣", 0.9),
        "alice_eve_friend": _ensure_relation(db_path, "alice_eve_friend", "friendship", "大学好友", 0.75),
        "alice_frank_friend": _ensure_relation(db_path, "alice_frank_friend", "friendship", "大学同学", 0.6),
        "bob_grace_family": _ensure_relation(db_path, "bob_grace_family", "family", "姐弟", 0.8),
        "carol_henry_mentor": _ensure_relation(db_path, "carol_henry_mentor", "authority", "导师/学徒", 0.8),
    }

    # 用 event 把关系挂到检索路径上
    _link_event_for_relation(db_path, relations["alice_bob_colleague"], [persons["alice"], persons["bob"]], "上季度一起打赢关键项目")
    _link_event_for_relation(db_path, relations["alice_dan_intimate"], [persons["alice"], persons["dan"]], "一起搬进新家")
    _link_event_for_relation(db_path, relations["alice_eve_friend"], [persons["alice"], persons["eve"]], "大学毕业十年聚会")
    _link_event_for_relation(db_path, relations["bob_grace_family"], [persons["bob"], persons["grace"]], "一起照顾生病的母亲")
    _link_event_for_relation(db_path, relations["carol_henry_mentor"], [persons["carol"], persons["henry"]], "持续指导 Carol 的职业路径")

    _ensure_memory_shared(db_path, "founding_weekend", "大家周末一起熬夜写 pitch deck",
                           [persons["alice"], persons["bob"], persons["carol"]], memory_type="shared_memory")
    _ensure_memory_shared(db_path, "date_night_sushi", "Alice 和 Dan 的寿司之夜",
                           [persons["alice"], persons["dan"]], memory_type="shared_memory")
    _ensure_memory_shared(db_path, "college_reunion", "Alice/Eve/Frank 的大学聚会",
                           [persons["alice"], persons["eve"], persons["frank"]], memory_type="shared_memory")

    work_scene = create_scene(
        db_path=db_path, scene_type="work_discussion", scene_summary="季度 sync",
        environment={"location_scope": "remote", "channel_scope": "group_channel",
                     "visibility_scope": "group_visible", "activation_barrier": "medium"},
        group_id=group_id,
    )
    for pid, state, score, is_speaking in [
        (persons["alice"], "explicit", 1.0, True),
        (persons["bob"], "explicit", 0.9, False),
        (persons["carol"], "latent", 0.7, False),
    ]:
        add_scene_participant(
            db_path=db_path, scene_id=work_scene, person_id=pid,
            activation_state=state, activation_score=score, is_speaking=is_speaking,
        )

    date_scene = create_scene(
        db_path=db_path, scene_type="intimate", scene_summary="晚间私聊",
        environment={"location_scope": "home", "channel_scope": "private_dm",
                     "visibility_scope": "mutual_visible", "activation_barrier": "low"},
    )
    add_scene_participant(db_path=db_path, scene_id=date_scene, person_id=persons["alice"],
                          activation_state="explicit", activation_score=1.0, is_speaking=True)
    add_scene_participant(db_path=db_path, scene_id=date_scene, person_id=persons["dan"],
                          activation_state="explicit", activation_score=0.95, is_speaking=False)

    reunion_scene = create_scene(
        db_path=db_path, scene_type="casual_social", scene_summary="老友聚会",
        environment={"location_scope": "offline_venue", "channel_scope": "group_channel",
                     "visibility_scope": "mutual_visible"},
    )
    add_scene_participant(db_path=db_path, scene_id=reunion_scene, person_id=persons["alice"],
                          activation_state="explicit", activation_score=1.0, is_speaking=True)
    add_scene_participant(db_path=db_path, scene_id=reunion_scene, person_id=persons["eve"],
                          activation_state="explicit", activation_score=0.9, is_speaking=False)
    add_scene_participant(db_path=db_path, scene_id=reunion_scene, person_id=persons["frank"],
                          activation_state="latent", activation_score=0.7, is_speaking=False)

    return {
        "persons": persons,
        "group_id": group_id,
        "relations": relations,
        "scenes": {
            "work": work_scene,
            "date": date_scene,
            "reunion": reunion_scene,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="灌入 Society C demo 数据集")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--tenant-id", default=None)
    args = parser.parse_args()
    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id)
    summary = seed_society_c(tenant_root)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
