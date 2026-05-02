import sqlite3
from pathlib import Path

from we_together.db.connection import connect
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch


def score_candidates(left: dict, right: dict) -> float:
    if (
        left.get("platform") == right.get("platform")
        and left.get("external_id")
        and left.get("external_id") == right.get("external_id")
    ):
        return 1.0

    if left.get("display_name") and left.get("display_name") == right.get("display_name"):
        return 0.7

    return 0.1


def find_and_merge_duplicates(db_path: Path, threshold: float = 0.7) -> dict:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT person_id, platform, external_id, display_name
        FROM identity_links
        WHERE person_id IN (SELECT person_id FROM persons WHERE status = 'active')
        ORDER BY person_id
        """,
    ).fetchall()
    conn.close()

    # 按 person_id 分组
    links_by_person: dict[str, list[dict]] = {}
    for row in rows:
        pid = row["person_id"]
        links_by_person.setdefault(pid, []).append({
            "platform": row["platform"],
            "external_id": row["external_id"],
            "display_name": row["display_name"],
        })

    person_ids = list(links_by_person.keys())
    merged_count = 0
    merged_set: set[str] = set()

    for i in range(len(person_ids)):
        pid_a = person_ids[i]
        if pid_a in merged_set:
            continue
        for j in range(i + 1, len(person_ids)):
            pid_b = person_ids[j]
            if pid_b in merged_set:
                continue

            best_score = 0.0
            for link_a in links_by_person[pid_a]:
                for link_b in links_by_person[pid_b]:
                    s = score_candidates(link_a, link_b)
                    if s > best_score:
                        best_score = s

            if best_score >= threshold:
                patch = build_patch(
                    source_event_id=f"evt_auto_merge_{pid_a}_{pid_b}",
                    target_type="person",
                    target_id=pid_a,
                    operation="merge_entities",
                    payload={
                        "source_person_id": pid_b,
                        "target_person_id": pid_a,
                    },
                    confidence=best_score,
                    reason=f"auto merge: score={best_score:.2f}",
                )
                apply_patch_record(db_path=db_path, patch=patch)
                merged_set.add(pid_b)
                merged_count += 1

    return {"merged_count": merged_count}
