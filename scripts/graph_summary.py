import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.services.tenant_router import (
    infer_tenant_id_from_db_path,
    resolve_tenant_root,
)


def build_graph_summary(db_path: Path) -> dict:
    tenant_id = infer_tenant_id_from_db_path(db_path)
    conn = sqlite3.connect(db_path)
    person_count = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    identity_count = conn.execute("SELECT COUNT(*) FROM identity_links").fetchone()[0]
    relation_count = conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
    scene_count = conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0]
    event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    snapshot_entity_count = conn.execute("SELECT COUNT(*) FROM snapshot_entities").fetchone()[0]
    retrieval_cache_count = conn.execute("SELECT COUNT(*) FROM retrieval_cache").fetchone()[0]
    scene_active_relation_count = conn.execute("SELECT COUNT(*) FROM scene_active_relations").fetchone()[0]
    open_local_branch_count = conn.execute(
        "SELECT COUNT(*) FROM local_branches WHERE status = 'open'"
    ).fetchone()[0]
    branch_candidate_count = conn.execute("SELECT COUNT(*) FROM branch_candidates").fetchone()[0]
    memory_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    state_count = conn.execute("SELECT COUNT(*) FROM states").fetchone()[0]
    patch_count = conn.execute("SELECT COUNT(*) FROM patches").fetchone()[0]
    candidate_status_rows = conn.execute(
        "SELECT status, COUNT(*) AS cnt FROM branch_candidates GROUP BY status"
    ).fetchall()
    candidate_status_distribution = {row[0]: row[1] for row in candidate_status_rows}

    # Phase 4 候选层计数
    candidate_layer_counts: dict[str, dict[str, int]] = {}
    for table in ("identity_candidates", "event_candidates", "facet_candidates",
                   "relation_clues", "group_clues"):
        rows = conn.execute(
            f"SELECT status, COUNT(*) FROM {table} GROUP BY status"
        ).fetchall()
        candidate_layer_counts[table] = {row[0]: row[1] for row in rows}

    person_facet_count = conn.execute("SELECT COUNT(*) FROM person_facets").fetchone()[0]

    people = [row[0] for row in conn.execute("SELECT primary_name FROM persons ORDER BY primary_name").fetchall()]
    conn.close()
    return {
        "tenant_id": tenant_id,
        "db_path": str(db_path),
        "person_count": person_count,
        "identity_count": identity_count,
        "relation_count": relation_count,
        "scene_count": scene_count,
        "event_count": event_count,
        "snapshot_entity_count": snapshot_entity_count,
        "retrieval_cache_count": retrieval_cache_count,
        "scene_active_relation_count": scene_active_relation_count,
        "open_local_branch_count": open_local_branch_count,
        "branch_candidate_count": branch_candidate_count,
        "memory_count": memory_count,
        "state_count": state_count,
        "patch_count": patch_count,
        "candidate_status_distribution": candidate_status_distribution,
        "candidate_layer_counts": candidate_layer_counts,
        "person_facet_count": person_facet_count,
        "people": people,
    }



def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize graph contents from SQLite")
    parser.add_argument("--root", default=str(ROOT), help="Project root containing db/main.sqlite3")
    parser.add_argument("--tenant-id", default=None)
    args = parser.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    print(json.dumps(build_graph_summary(db_path), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
