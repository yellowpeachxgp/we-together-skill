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
            "display_name": row["person_id"],
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
        "active_relations": [],
        "relevant_memories": [],
        "current_states": [],
        "activation_map": activation_map,
        "response_policy": response_policy,
        "safety_and_budget": {},
    }
