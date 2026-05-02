"""记忆凝练：把同主题的 memory cluster 压成单条 summary_memory。

流程：
  1. cluster_memories 得分组
  2. 对每个 cluster 调 LLM 生成 summary
  3. 通过 create_memory patch 写入一条新 memory（memory_type='condensed_memory'）
  4. metadata_json.refs = 原 memory_ids；owners = cluster.owner_ids

受 max_clusters 限制，避免一次跑爆。
"""
from __future__ import annotations

import uuid
from pathlib import Path

from we_together.db.connection import connect
from we_together.llm import LLMMessage, get_llm_client
from we_together.services.memory_cluster_service import cluster_memories
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch


def _build_prompt(cluster: dict, memory_summaries: list[str]) -> list[LLMMessage]:
    bullets = "\n".join(f"- {s}" for s in memory_summaries)
    return [
        LLMMessage(role="system", content="你是记忆凝练助手。把多条相关 memory 压成 1 条精炼摘要。"),
        LLMMessage(
            role="user",
            content=(
                f"以下是 {len(memory_summaries)} 条同主题 memory：\n{bullets}\n"
                "请输出 JSON：{\"summary\": \"一句话摘要\"}"
            ),
        ),
    ]


def condense_memory_clusters(
    db_path: Path,
    *,
    min_cluster_size: int = 2,
    owner_overlap_threshold: float = 0.5,
    max_clusters: int = 20,
    llm_client=None,
    source_event_id: str | None = None,
) -> dict:
    clusters = cluster_memories(
        db_path,
        min_cluster_size=min_cluster_size,
        owner_overlap_threshold=owner_overlap_threshold,
    )
    clusters = clusters[:max_clusters]

    client = llm_client or get_llm_client()
    created: list[dict] = []

    for cluster in clusters:
        conn = connect(db_path)
        summaries = [
            r[0]
            for r in conn.execute(
                f"SELECT summary FROM memories WHERE memory_id IN ({','.join('?' for _ in cluster['memory_ids'])})",
                tuple(cluster["memory_ids"]),
            ).fetchall()
        ]
        conn.close()

        try:
            payload = client.chat_json(
                _build_prompt(cluster, summaries),
                schema_hint={"summary": "str"},
            )
            summary_text = str(payload.get("summary", "") or "").strip()
        except Exception:
            summary_text = ""
        if not summary_text:
            summary_text = f"{len(summaries)} 条 {cluster['memory_type']} 记忆的凝练"

        new_id = f"mem_cond_{uuid.uuid4().hex[:10]}"
        patch = build_patch(
            source_event_id=source_event_id or f"condense_{cluster['cluster_id']}",
            target_type="memory",
            target_id=new_id,
            operation="create_memory",
            payload={
                "memory_id": new_id,
                "memory_type": "condensed_memory",
                "summary": summary_text,
                "relevance_score": 0.7,
                "confidence": 0.65,
                "is_shared": 1,
                "status": "active",
                "metadata_json": {
                    "condensed_from": cluster["memory_ids"],
                    "cluster_id": cluster["cluster_id"],
                    "source_memory_type": cluster["memory_type"],
                },
            },
            confidence=0.65,
            reason=f"condense {len(cluster['memory_ids'])} memories",
        )
        apply_patch_record(db_path=db_path, patch=patch)

        owner_conn = connect(db_path)
        for pid in cluster["owner_ids"]:
            owner_conn.execute(
                "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
                "VALUES(?, 'person', ?, 'condensed')",
                (new_id, pid),
            )
        owner_conn.commit()
        owner_conn.close()

        created.append({
            "memory_id": new_id,
            "cluster_id": cluster["cluster_id"],
            "refs": cluster["memory_ids"],
            "summary": summary_text,
        })

    return {
        "condensed_count": len(created),
        "created": created,
        "cluster_count": len(clusters),
    }
