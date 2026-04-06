from pathlib import Path
import sqlite3


def build_runtime_retrieval_package_from_db(db_path: Path, scene_id: str) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    scene = conn.execute("SELECT * FROM scenes WHERE scene_id = ?", (scene_id,)).fetchone()
    participants_rows = conn.execute(
        "SELECT * FROM scene_participants WHERE scene_id = ?",
        (scene_id,),
    ).fetchall()
    person_rows = conn.execute(
        "SELECT person_id, primary_name FROM persons WHERE person_id IN (%s)"
        % ",".join("?" for _ in participants_rows),
        tuple(row["person_id"] for row in participants_rows),
    ).fetchall() if participants_rows else []
    person_names = {row["person_id"]: row["primary_name"] for row in person_rows}

    active_relations = []
    relevant_memories = []
    if len(participants_rows) >= 2:
        relation_rows = conn.execute("SELECT relation_id, core_type, custom_label, summary, status, strength FROM relations").fetchall()
        event_targets = conn.execute(
            "SELECT DISTINCT target_id FROM event_targets WHERE target_type = 'relation'"
        ).fetchall()
        relation_ids = {row["target_id"] for row in event_targets}
        for relation in relation_rows:
            if relation["relation_id"] not in relation_ids:
                continue
            active_relations.append(
                {
                    "relation_id": relation["relation_id"],
                    "core_type": relation["core_type"],
                    "custom_label": relation["custom_label"],
                    "status": relation["status"],
                    "strength": relation["strength"],
                    "short_summary": relation["summary"],
                }
            )
        memory_rows = conn.execute(
            """
            SELECT DISTINCT m.memory_id, m.summary, m.memory_type, m.relevance_score, m.confidence
            FROM memories m
            JOIN memory_owners mo ON mo.memory_id = m.memory_id
            WHERE mo.owner_id IN (%s)
            AND m.is_shared = 1
            ORDER BY m.relevance_score DESC, m.created_at DESC
            """
            % ",".join("?" for _ in participants_rows),
            tuple(row["person_id"] for row in participants_rows),
        ).fetchall()
        relevant_memories = [
            {
                "memory_id": row["memory_id"],
                "memory_type": row["memory_type"],
                "summary": row["summary"],
                "relevance_score": row["relevance_score"],
                "confidence": row["confidence"],
            }
            for row in memory_rows
        ]
    conn.close()

    scene_summary = {
        "scene_id": scene["scene_id"],
        "scene_type": scene["scene_type"],
        "summary": scene["scene_summary"],
    }
    environment_constraints = {
        "location_scope": scene["location_scope"],
        "channel_scope": scene["channel_scope"],
        "visibility_scope": scene["visibility_scope"],
        "time_scope": scene["time_scope"],
        "role_scope": scene["role_scope"],
        "access_scope": scene["access_scope"],
        "privacy_scope": scene["privacy_scope"],
        "activation_barrier": scene["activation_barrier"],
    }
    participants = [
        {
            "person_id": row["person_id"],
            "display_name": person_names.get(row["person_id"], row["person_id"]),
            "scene_role": "participant",
            "speak_eligibility": "allowed" if row["is_speaking"] else "discouraged",
        }
        for row in participants_rows
    ]
    activation_map = [
        {
            "person_id": row["person_id"],
            "activation_score": row["activation_score"],
            "activation_state": row["activation_state"],
            "activation_reason_summary": "scene participant",
        }
        for row in participants_rows
    ]
    primary = next((row["person_id"] for row in participants_rows if row["is_speaking"]), None)
    response_policy = {
        "mode": "single_primary" if primary else "primary_plus_support",
        "primary_speaker": primary,
        "supporting_speakers": [],
        "silenced_participants": [row["person_id"] for row in participants_rows if not row["is_speaking"]],
        "reason": "derived from scene participants",
    }

    return {
        "scene_summary": scene_summary,
        "environment_constraints": environment_constraints,
        "participants": participants,
        "active_relations": active_relations,
        "relevant_memories": relevant_memories,
        "current_states": [],
        "activation_map": activation_map,
        "response_policy": response_policy,
        "safety_and_budget": {},
    }
