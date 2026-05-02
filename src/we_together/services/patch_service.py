import uuid
from datetime import UTC, datetime


def build_patch(
    source_event_id: str,
    target_type: str,
    target_id: str | None,
    operation: str,
    payload: dict,
    confidence: float,
    reason: str,
) -> dict:
    return {
        "patch_id": f"patch_{uuid.uuid4().hex}",
        "source_event_id": source_event_id,
        "target_type": target_type,
        "target_id": target_id,
        "operation": operation,
        "payload_json": payload,
        "confidence": confidence,
        "reason": reason,
        "status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
        "applied_at": None,
    }


def infer_narration_patches(
    source_event_id: str,
    text: str,
    person_ids: list[str],
    relation_ids: list[str],
) -> list[dict]:
    if len(person_ids) < 2:
        return []

    memory_id = f"memory_{uuid.uuid5(uuid.NAMESPACE_URL, f'memory:{person_ids[0]}:{person_ids[1]}:{text}').hex}"
    patches = [
        build_patch(
            source_event_id=source_event_id,
            target_type="memory",
            target_id=memory_id,
            operation="create_memory",
            payload={
                "memory_id": memory_id,
                "memory_type": "shared_memory",
                "summary": text,
                "relevance_score": 1.0,
                "confidence": 0.7,
                "is_shared": 1,
                "status": "active",
                "metadata_json": {"source_event_id": source_event_id},
            },
            confidence=0.7,
            reason="narration inferred shared memory",
        )
    ]

    for relation_id in relation_ids:
        patches.append(
            build_patch(
                source_event_id=source_event_id,
                target_type="entity_link",
                target_id=None,
                operation="link_entities",
                payload={
                    "from_type": "relation",
                    "from_id": relation_id,
                    "relation_type": "supported_by_memory",
                    "to_type": "memory",
                    "to_id": memory_id,
                    "weight": 0.7,
                    "metadata_json": {"source_event_id": source_event_id},
                },
                confidence=0.7,
                reason="narration linked relation to inferred shared memory",
            )
        )
        if "朋友" in text:
            state_id = f"state_{uuid.uuid5(uuid.NAMESPACE_URL, f'relation-tone:{relation_id}:{text}').hex}"
            patches.append(
                build_patch(
                    source_event_id=source_event_id,
                    target_type="state",
                    target_id=state_id,
                    operation="update_state",
                    payload={
                        "state_id": state_id,
                        "scope_type": "relation",
                        "scope_id": relation_id,
                        "state_type": "tone",
                        "value_json": {"tone": "friendly"},
                        "confidence": 0.7,
                        "is_inferred": 1,
                        "source_event_refs_json": [source_event_id],
                    },
                    confidence=0.7,
                    reason="narration inferred friendly relation tone",
                )
            )

    return patches


def infer_text_chat_patches(
    source_event_id: str,
    transcript: str,
    person_ids: list[str],
    relation_id: str,
) -> list[dict]:
    if len(person_ids) < 2:
        return []

    summary = "来源于文本聊天导入"
    memory_id = f"memory_{uuid.uuid5(uuid.NAMESPACE_URL, f'text_chat:{person_ids[0]}:{person_ids[1]}:{summary}').hex}"
    patches = [
        build_patch(
            source_event_id=source_event_id,
            target_type="memory",
            target_id=memory_id,
            operation="create_memory",
            payload={
                "memory_id": memory_id,
                "memory_type": "shared_memory",
                "summary": summary,
                "relevance_score": 0.8,
                "confidence": 0.6,
                "is_shared": 1,
                "status": "active",
                "metadata_json": {"source_event_id": source_event_id},
            },
            confidence=0.6,
            reason="text chat inferred shared memory",
        ),
        build_patch(
            source_event_id=source_event_id,
            target_type="entity_link",
            target_id=None,
            operation="link_entities",
            payload={
                "from_type": "relation",
                "from_id": relation_id,
                "relation_type": "supported_by_memory",
                "to_type": "memory",
                "to_id": memory_id,
                "weight": 0.5,
                "metadata_json": {"source_event_id": source_event_id},
            },
            confidence=0.5,
            reason="text chat linked relation to inferred memory",
        ),
    ]
    if "累" in transcript:
        state_id = f"state_{uuid.uuid5(uuid.NAMESPACE_URL, f'text-chat-energy:{person_ids[0]}:{transcript}').hex}"
        patches.append(
            build_patch(
                source_event_id=source_event_id,
                target_type="state",
                target_id=state_id,
                operation="update_state",
                payload={
                    "state_id": state_id,
                    "scope_type": "person",
                    "scope_id": person_ids[0],
                    "state_type": "energy",
                    "value_json": {"energy": "low", "summary": "tired"},
                    "confidence": 0.6,
                    "is_inferred": 1,
                    "source_event_refs_json": [source_event_id],
                },
                confidence=0.6,
                reason="text chat inferred low energy state",
            )
        )
    return patches


def infer_email_patches(
    source_event_id: str,
    person_id: str,
    summary: str,
) -> list[dict]:
    memory_id = f"memory_{uuid.uuid5(uuid.NAMESPACE_URL, f'email:{person_id}:{summary}').hex}"
    patches = [
        build_patch(
            source_event_id=source_event_id,
            target_type="memory",
            target_id=memory_id,
            operation="create_memory",
            payload={
                "memory_id": memory_id,
                "memory_type": "shared_memory",
                "summary": summary,
                "relevance_score": 0.9,
                "confidence": 0.75,
                "is_shared": 1,
                "status": "active",
                "metadata_json": {"source_event_id": source_event_id},
            },
            confidence=0.75,
            reason="email inferred shared memory",
        )
    ]
    patches.append(
        build_patch(
            source_event_id=source_event_id,
            target_type="entity_link",
            target_id=None,
            operation="link_entities",
            payload={
                "from_type": "person",
                "from_id": person_id,
                "relation_type": "supports",
                "to_type": "memory",
                "to_id": memory_id,
                "weight": 0.7,
                "metadata_json": {"source_event_id": source_event_id},
            },
            confidence=0.7,
            reason="email linked person to inferred memory",
        )
    )
    if "顺利" in summary:
        state_id = f"state_{uuid.uuid5(uuid.NAMESPACE_URL, f'email-work-status:{person_id}:{summary}').hex}"
        patches.append(
            build_patch(
                source_event_id=source_event_id,
                target_type="state",
                target_id=state_id,
                operation="update_state",
                payload={
                    "state_id": state_id,
                    "scope_type": "person",
                    "scope_id": person_id,
                    "state_type": "work_status",
                    "value_json": {"status": "on_track", "sentiment": "positive"},
                    "confidence": 0.75,
                    "is_inferred": 1,
                    "source_event_refs_json": [source_event_id],
                },
                confidence=0.75,
                reason="email inferred positive work status",
            )
        )
    return patches


def infer_dialogue_patches(
    source_event_id: str,
    scene_id: str,
    user_input: str,
    response_text: str,
    speaking_person_ids: list[str] | None = None,
) -> list[dict]:
    patches = []
    combined = f"{user_input} {response_text}"

    # 场景气氛 state
    tone = "neutral"
    if any(w in combined for w in ("顺利", "好", "开心", "太好了", "高兴")):
        tone = "positive"
    elif any(w in combined for w in ("累", "烦", "难", "糟糕", "不好")):
        tone = "negative"

    state_id = f"state_{uuid.uuid5(uuid.NAMESPACE_URL, f'dialogue-mood:{scene_id}:{source_event_id}').hex}"
    patches.append(
        build_patch(
            source_event_id=source_event_id,
            target_type="state",
            target_id=state_id,
            operation="update_state",
            payload={
                "state_id": state_id,
                "scope_type": "scene",
                "scope_id": scene_id,
                "state_type": "mood",
                "value_json": {"tone": tone, "source": "dialogue"},
                "confidence": 0.6,
                "is_inferred": 1,
                "source_event_refs_json": [source_event_id],
            },
            confidence=0.6,
            reason="dialogue inferred scene mood",
        )
    )

    # 有多人发言时创建共享记忆
    speakers = speaking_person_ids or []
    if len(speakers) >= 2:
        summary = f"对话: {user_input[:60]}"
        memory_id = f"memory_{uuid.uuid5(uuid.NAMESPACE_URL, f'dialogue:{speakers[0]}:{speakers[1]}:{source_event_id}').hex}"
        patches.append(
            build_patch(
                source_event_id=source_event_id,
                target_type="memory",
                target_id=memory_id,
                operation="create_memory",
                payload={
                    "memory_id": memory_id,
                    "memory_type": "shared_memory",
                    "summary": summary,
                    "relevance_score": 0.8,
                    "confidence": 0.6,
                    "is_shared": 1,
                    "status": "active",
                    "metadata_json": {"source_event_id": source_event_id},
                },
                confidence=0.6,
                reason="dialogue inferred shared memory",
            )
        )

    return patches
