import json
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect
from we_together.runtime.sqlite_retrieval import invalidate_runtime_retrieval_cache


def _ensure_patch_record(conn, patch: dict) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO patches(
            patch_id, source_event_id, target_type, target_id,
            operation, payload_json, confidence, reason, status,
            created_at, applied_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patch["patch_id"],
            patch["source_event_id"],
            patch["target_type"],
            patch["target_id"],
            patch["operation"],
            json.dumps(patch["payload_json"], ensure_ascii=False),
            patch["confidence"],
            patch["reason"],
            patch.get("status", "pending"),
            patch["created_at"],
            patch.get("applied_at"),
        ),
    )


def apply_patch_record(db_path: Path, patch: dict) -> None:
    conn = connect(db_path)
    _ensure_patch_record(conn, patch)
    payload = patch["payload_json"]
    now = datetime.now(UTC).isoformat()

    if patch["operation"] == "create_memory":
        conn.execute(
            """
            INSERT OR REPLACE INTO memories(
                memory_id, memory_type, summary, emotional_tone, relevance_score,
                confidence, is_shared, status, metadata_json, created_at, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["memory_id"],
                payload["memory_type"],
                payload["summary"],
                payload.get("emotional_tone"),
                payload.get("relevance_score"),
                payload.get("confidence"),
                payload.get("is_shared", 0),
                payload.get("status", "active"),
                json.dumps(payload.get("metadata_json", {}), ensure_ascii=False),
                now,
                now,
            ),
        )
    elif patch["operation"] == "update_state":
        conn.execute(
            """
            INSERT OR REPLACE INTO states(
                state_id, scope_type, scope_id, state_type, value_json,
                confidence, is_inferred, decay_policy, source_event_refs_json,
                created_at, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["state_id"],
                payload["scope_type"],
                payload["scope_id"],
                payload["state_type"],
                json.dumps(payload["value_json"], ensure_ascii=False),
                payload.get("confidence"),
                payload.get("is_inferred", 1),
                payload.get("decay_policy"),
                json.dumps(payload.get("source_event_refs_json", []), ensure_ascii=False),
                now,
                now,
            ),
        )
    elif patch["operation"] == "link_entities":
        conn.execute(
            """
            DELETE FROM entity_links
            WHERE from_type = ?
            AND from_id = ?
            AND relation_type = ?
            AND to_type = ?
            AND to_id = ?
            """,
            (
                payload["from_type"],
                payload["from_id"],
                payload["relation_type"],
                payload["to_type"],
                payload["to_id"],
            ),
        )
        conn.execute(
            """
            INSERT INTO entity_links(
                from_type, from_id, relation_type, to_type, to_id, weight, metadata_json
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["from_type"],
                payload["from_id"],
                payload["relation_type"],
                payload["to_type"],
                payload["to_id"],
                payload.get("weight"),
                json.dumps(payload.get("metadata_json", {}), ensure_ascii=False),
            ),
        )
    elif patch["operation"] == "create_local_branch":
        conn.execute(
            """
            INSERT OR REPLACE INTO local_branches(
                branch_id, scope_type, scope_id, status, reason,
                created_from_event_id, created_at, resolved_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["branch_id"],
                payload["scope_type"],
                payload["scope_id"],
                payload.get("status", "open"),
                payload.get("reason"),
                payload.get("created_from_event_id"),
                payload.get("created_at", now),
                payload.get("resolved_at"),
            ),
        )
        branch_candidates = payload.get("branch_candidates") or []
        if branch_candidates:
            conn.executemany(
                """
                INSERT OR REPLACE INTO branch_candidates(
                    candidate_id, branch_id, label, payload_json,
                    confidence, status, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        candidate["candidate_id"],
                        payload["branch_id"],
                        candidate.get("label"),
                        json.dumps(candidate["payload_json"], ensure_ascii=False),
                        candidate.get("confidence"),
                        candidate.get("status", "open"),
                        candidate.get("created_at", now),
                    )
                    for candidate in branch_candidates
                ],
            )
    elif patch["operation"] == "resolve_local_branch":
        selected_candidate_id = payload.get("selected_candidate_id")
        candidate_row = None
        effect_patches = None
        if selected_candidate_id is not None:
            candidate_row = conn.execute(
                """
                SELECT payload_json
                FROM branch_candidates
                WHERE candidate_id = ? AND branch_id = ?
                """,
                (selected_candidate_id, payload["branch_id"]),
            ).fetchone()
            if candidate_row is None:
                conn.execute(
                    "UPDATE patches SET status = ?, applied_at = ? WHERE patch_id = ?",
                    ("failed", now, patch["patch_id"]),
                )
                conn.commit()
                conn.close()
                raise ValueError("selected candidate does not belong to branch")
            candidate_payload = json.loads(candidate_row[0])
            effect_patches = candidate_payload.get("effect_patches")

        if effect_patches:
            conn.commit()
            conn.close()
            from we_together.services.patch_service import build_patch as _build_patch

            try:
                for effect in effect_patches:
                    effect_patch = _build_patch(
                        source_event_id=patch["source_event_id"],
                        target_type=effect["target_type"],
                        target_id=effect["target_id"],
                        operation=effect["operation"],
                        payload=effect["payload"],
                        confidence=effect.get("confidence", patch["confidence"]),
                        reason=effect.get("reason", "effect from resolved candidate"),
                    )
                    apply_patch_record(db_path=db_path, patch=effect_patch)
            except Exception:
                conn = connect(db_path)
                try:
                    conn.execute(
                        "UPDATE patches SET status = ?, applied_at = ? WHERE patch_id = ?",
                        ("failed", now, patch["patch_id"]),
                    )
                    conn.commit()
                finally:
                    conn.close()
                raise

            conn = connect(db_path)

        conn.execute(
            """
            UPDATE local_branches
            SET status = ?, reason = ?, resolved_at = ?
            WHERE branch_id = ?
            """,
            (
                payload.get("status", "resolved"),
                payload.get("reason"),
                payload.get("resolved_at", now),
                payload["branch_id"],
            ),
        )
        if selected_candidate_id is not None:
            conn.execute(
                """
                UPDATE branch_candidates
                SET status = CASE
                    WHEN candidate_id = ? THEN 'selected'
                    ELSE 'rejected'
                END
                WHERE branch_id = ?
                """,
                (selected_candidate_id, payload["branch_id"]),
            )
    elif patch["operation"] == "unlink_entities":
        conn.execute(
            """
            DELETE FROM entity_links
            WHERE from_type = ?
            AND from_id = ?
            AND relation_type = ?
            AND to_type = ?
            AND to_id = ?
            """,
            (
                payload["from_type"],
                payload["from_id"],
                payload["relation_type"],
                payload["to_type"],
                payload["to_id"],
            ),
        )
    elif patch["operation"] == "update_entity":
        table_by_target = {
            "person": ("persons", "person_id"),
            "relation": ("relations", "relation_id"),
            "group": ("groups", "group_id"),
            "memory": ("memories", "memory_id"),
        }
        entry = table_by_target.get(patch["target_type"])
        if entry is None or patch["target_id"] is None:
            conn.execute(
                "UPDATE patches SET status = ?, applied_at = ? WHERE patch_id = ?",
                ("failed", now, patch["patch_id"]),
            )
            conn.commit()
            conn.close()
            raise ValueError(f"Unsupported update_entity target: {patch['target_type']}")

        table_name, id_column = entry
        set_clauses = []
        params = []
        for field_name, field_value in payload.items():
            set_clauses.append(f"{field_name} = ?")
            params.append(field_value)
        set_clauses.append("updated_at = ?")
        params.append(now)
        params.append(patch["target_id"])
        conn.execute(
            f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {id_column} = ?",
            tuple(params),
        )
    elif patch["operation"] == "mark_inactive":
        table_by_target = {
            "memory": "memories",
            "relation": "relations",
            "person": "persons",
            "group": "groups",
        }
        table_name = table_by_target.get(patch["target_type"])
        if table_name is None or patch["target_id"] is None:
            conn.execute(
                "UPDATE patches SET status = ?, applied_at = ? WHERE patch_id = ?",
                ("failed", now, patch["patch_id"]),
            )
            conn.commit()
            conn.close()
            raise ValueError(f"Unsupported mark_inactive target: {patch['target_type']}")

        id_column = f"{patch['target_type']}_id"
        conn.execute(
            f"UPDATE {table_name} SET status = ?, updated_at = ? WHERE {id_column} = ?",
            ("inactive", now, patch["target_id"]),
        )
    elif patch["operation"] == "merge_entities":
        source_pid = payload["source_person_id"]
        target_pid = payload["target_person_id"]

        # 迁移 identity_links
        conn.execute(
            "UPDATE identity_links SET person_id = ? WHERE person_id = ?",
            (target_pid, source_pid),
        )
        # 迁移 event_participants
        conn.execute(
            "UPDATE OR IGNORE event_participants SET person_id = ? WHERE person_id = ?",
            (target_pid, source_pid),
        )
        conn.execute(
            "DELETE FROM event_participants WHERE person_id = ?",
            (source_pid,),
        )
        # 迁移 memory_owners
        conn.execute(
            "UPDATE OR IGNORE memory_owners SET owner_id = ? WHERE owner_type = 'person' AND owner_id = ?",
            (target_pid, source_pid),
        )
        conn.execute(
            "DELETE FROM memory_owners WHERE owner_type = 'person' AND owner_id = ?",
            (source_pid,),
        )
        # 迁移 scene_participants
        conn.execute(
            "UPDATE OR IGNORE scene_participants SET person_id = ? WHERE person_id = ?",
            (target_pid, source_pid),
        )
        conn.execute(
            "DELETE FROM scene_participants WHERE person_id = ?",
            (source_pid,),
        )
        # 迁移 group_members
        conn.execute(
            "UPDATE OR IGNORE group_members SET person_id = ? WHERE person_id = ?",
            (target_pid, source_pid),
        )
        conn.execute(
            "DELETE FROM group_members WHERE person_id = ?",
            (source_pid,),
        )
        # 标记 source person 为 merged
        existing_meta = conn.execute(
            "SELECT metadata_json FROM persons WHERE person_id = ?",
            (source_pid,),
        ).fetchone()
        meta = json.loads(existing_meta[0]) if existing_meta and existing_meta[0] else {}
        meta["merged_into"] = target_pid
        conn.execute(
            "UPDATE persons SET status = 'merged', metadata_json = ?, updated_at = ? WHERE person_id = ?",
            (json.dumps(meta, ensure_ascii=False), now, source_pid),
        )
    elif patch["operation"] == "unmerge_person":
        conn.commit()
        conn.close()
        from we_together.services.entity_unmerge_service import unmerge_person

        try:
            unmerge_person(
                db_path,
                payload["source_person_id"],
                reviewer=payload.get("reviewer", "operator_gate"),
                reason=payload.get("reason", patch["reason"]),
            )
        except Exception:
            conn = connect(db_path)
            try:
                conn.execute(
                    "UPDATE patches SET status = ?, applied_at = ? WHERE patch_id = ?",
                    ("failed", now, patch["patch_id"]),
                )
                conn.commit()
            finally:
                conn.close()
            raise

        conn = connect(db_path)
        try:
            conn.execute(
                "UPDATE patches SET status = ?, applied_at = ? WHERE patch_id = ?",
                ("applied", now, patch["patch_id"]),
            )
            conn.commit()
        finally:
            conn.close()
        invalidate_runtime_retrieval_cache(db_path=db_path)
        try:
            from we_together.observability.metrics import counter_inc
            counter_inc(
                "patches_applied",
                labels={"operation": patch.get("operation", "unknown")},
            )
        except Exception:
            pass
        return
    elif patch["operation"] == "upsert_facet":
        facet_id = payload.get("facet_id") or f"facet_{patch['patch_id'][-16:]}"
        value_json = payload.get("facet_value_json")
        if value_json is None:
            # 允许传入 facet_value + scope_hint + metadata_json，组合成 facet_value_json
            value_json = {
                "value": payload.get("facet_value"),
                "scope_hint": payload.get("scope_hint"),
                "metadata": payload.get("metadata_json", {}),
            }
        existing = conn.execute(
            """
            SELECT facet_id FROM person_facets
            WHERE person_id = ? AND facet_type = ? AND facet_key = ?
            """,
            (payload["person_id"], payload["facet_type"], payload["facet_key"]),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE person_facets
                SET facet_value_json = ?, confidence = ?,
                    source_event_refs_json = ?, updated_at = ?
                WHERE facet_id = ?
                """,
                (
                    json.dumps(value_json, ensure_ascii=False),
                    payload.get("confidence"),
                    json.dumps(payload.get("source_event_refs_json", []), ensure_ascii=False),
                    now,
                    existing[0],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO person_facets(
                    facet_id, person_id, facet_type, facet_key,
                    facet_value_json, confidence, source_event_refs_json,
                    created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    facet_id,
                    payload["person_id"],
                    payload["facet_type"],
                    payload["facet_key"],
                    json.dumps(value_json, ensure_ascii=False),
                    payload.get("confidence"),
                    json.dumps(payload.get("source_event_refs_json", []), ensure_ascii=False),
                    now,
                    now,
                ),
            )
    else:
        conn.execute(
            "UPDATE patches SET status = ?, applied_at = ? WHERE patch_id = ?",
            ("failed", now, patch["patch_id"]),
        )
        conn.commit()
        conn.close()
        raise ValueError(f"Unsupported patch operation: {patch['operation']}")

    conn.execute(
        "UPDATE patches SET status = ?, applied_at = ? WHERE patch_id = ?",
        ("applied", now, patch["patch_id"]),
    )
    conn.commit()
    conn.close()
    invalidate_runtime_retrieval_cache(db_path=db_path)
    # Phase 12 metrics 埋点
    try:
        from we_together.observability.metrics import counter_inc
        counter_inc("patches_applied", labels={"operation": patch.get("operation", "unknown")})
    except Exception:
        pass
