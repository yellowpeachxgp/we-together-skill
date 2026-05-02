"""Invariant Registry（Phase 58 / ADR 0060）。

**目的**：
we-together 至 v0.17 累计 28 条不变式。过去它们在 ADR 里写明但**缺少强制测试映射**。
Phase 58 把每条不变式绑定到至少 1 个 pytest 测试 ID，违反时 CI 立即红。

不变式 #29（本期新增）：纸面不变式禁止——每条不变式必须有 >= 1 个覆盖测试。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Invariant:
    id: int
    phase: str
    title: str
    description: str
    adr_refs: list[str] = field(default_factory=list)
    test_refs: list[str] = field(default_factory=list)  # "tests/path::test_name"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "phase": self.phase, "title": self.title,
            "description": self.description,
            "adr_refs": list(self.adr_refs),
            "test_refs": list(self.test_refs),
            "covered": len(self.test_refs) > 0,
        }


INVARIANTS: list[Invariant] = [
    Invariant(
        id=1, phase="P1", title="事件优先",
        description="演化总是先写 event，再推理 patch，再改图谱",
        adr_refs=["ADR 0001"],
        test_refs=["tests/services/test_patch_application.py::test_apply_patch_record_can_create_memory"],
    ),
    Invariant(
        id=2, phase="P1", title="局部分支",
        description="仅对未决歧义开 local_branch，不做整图分叉",
        adr_refs=["ADR 0001"],
        test_refs=["tests/services/test_branch_resolver.py::test_resolver_runs"],
    ),
    Invariant(
        id=3, phase="P1", title="默认自动化 + 底层可逆",
        description="identity 融合激进，但通过 merge_entities 可追溯",
        adr_refs=["ADR 0001"],
        test_refs=["tests/services/test_identity_fusion.py::test_score_basic"],
    ),
    Invariant(
        id=4, phase="P1", title="摘要是派生视图",
        description="persona_summary / style_summary 等是派生字段",
        adr_refs=["ADR 0001"],
        test_refs=["tests/services/test_phase_55_df.py::test_get_insight_sources_returns_source_memory_ids"],
    ),
    Invariant(
        id=5, phase="P1", title="Skill-first 通用型",
        description="运行时逻辑不绑死宿主平台",
        adr_refs=["ADR 0019"],
        test_refs=["tests/runtime/test_phase_33_skill_host.py::test_adapters_equivalent_payload_structure"],
    ),
    # Phase 13-18 累积（来自 ADR 0019 / 0023 的 6 → 14 条）
    Invariant(
        id=6, phase="P8-12", title="retrieval_package 字段版本化",
        description="retrieval_package 结构版本化，向后兼容",
        adr_refs=["ADR 0019"],
        test_refs=["tests/runtime/test_retrieval_package.py::test_build_basic"],
    ),
    Invariant(
        id=7, phase="P8-12", title="Skill 接口双路径",
        description="LLM 真路径 + Mock 必须语义等价",
        adr_refs=["ADR 0023"],
        test_refs=["tests/runtime/test_adapters.py::test_claude_adapter_build"],
    ),
    Invariant(
        id=8, phase="P8-12", title="bootstrap 幂等",
        description="重复 bootstrap 不污染图谱",
        adr_refs=["ADR 0019"],
        test_refs=["tests/db/test_bootstrap.py::test_bootstrap_is_idempotent"],
    ),
    Invariant(
        id=9, phase="P13-17", title="state 可衰减",
        description="state 有 decay_policy，不能永久高置信",
        adr_refs=["ADR 0016"],
        test_refs=["tests/services/test_state_decay.py::test_decay_linear_policy"],
    ),
    Invariant(
        id=10, phase="P13-17", title="relation 漂移 smallstep",
        description="relation.strength 每 event 最多 ±0.05",
        adr_refs=["ADR 0016"],
        test_refs=["tests/services/test_relation_drift.py::test_drift_window_limits"],
    ),
    Invariant(
        id=11, phase="P18-21", title="importer 输出契约",
        description="所有 importer 必须产 event + raw_evidence + candidate",
        adr_refs=["ADR 0019"],
        test_refs=["tests/importers/test_real_world_importers.py::test_imessage_importer_reads_candidates"],
    ),
    Invariant(
        id=12, phase="P18-21", title="snapshot 可回滚",
        description="任意 snapshot 可被 rollback_to_snapshot 恢复",
        adr_refs=["ADR 0016"],
        test_refs=["tests/services/test_snapshot_service.py::test_rollback_removes_later_patches"],
    ),
    Invariant(
        id=13, phase="P22-24", title="联邦 stub / graph_serializer JSON 规范",
        description="graph_serializer JSON schema 版本化",
        adr_refs=["ADR 0020", "ADR 0023"],
        test_refs=["tests/services/test_phase_22_interop.py::test_canonical_roundtrip"],
    ),
    Invariant(
        id=14, phase="P22-24", title="narrative 派生可重建",
        description="narrative_arcs 必须 source_event_refs 非空",
        adr_refs=["ADR 0022"],
        test_refs=["tests/services/test_phase_55_df.py::test_verify_narrative_arcs_rebuildable_missing"],
    ),
    Invariant(
        id=15, phase="P25-27", title="LLM 能力测试走 Mock",
        description="core path 不得在 import 阶段 require 真 SDK",
        adr_refs=["ADR 0027"],
        test_refs=["tests/services/test_phase_36_debt.py::test_llm_providers_delayed_import"],
    ),
    Invariant(
        id=16, phase="P25-27", title="向量能力 BLOB 契约 + 纯 Python",
        description="encode/decode/cosine 纯 Python；真规模交外部库",
        adr_refs=["ADR 0027"],
        test_refs=["tests/services/test_phase_26_embedding.py::test_encode_decode_roundtrip"],
    ),
    Invariant(
        id=17, phase="P29", title="多 agent 共享底层图谱",
        description="private vs shared 是查询过滤，不是物理拷贝",
        adr_refs=["ADR 0033"],
        test_refs=["tests/services/test_phase_29_30_31_32.py::test_person_agent_from_db"],
    ),
    Invariant(
        id=18, phase="P30", title="主动写入经预算+偏好门控",
        description="Detection-only 服务不直接改业务表",
        adr_refs=["ADR 0033"],
        test_refs=["tests/services/test_phase_29_30_31_32.py::test_check_budget_limits"],
    ),
    Invariant(
        id=19, phase="P33", title="SkillRuntime schema 版本化",
        description="破坏性变更需 v2，不 in-place 改",
        adr_refs=["ADR 0034"],
        test_refs=["tests/runtime/test_phase_33_skill_host.py::test_skill_request_rejects_wrong_version"],
    ),
    Invariant(
        id=20, phase="P34", title="tick 写入可回滚",
        description="tick 级 snapshot 可回滚至任一时间点",
        adr_refs=["ADR 0036"],
        test_refs=["tests/services/test_phase_39_ct.py::test_simulate_writes_real_snapshots"],
    ),
    Invariant(
        id=21, phase="P40", title="激活可 introspect",
        description="recent_traces / query_path / multi_hop 可序列化",
        adr_refs=["ADR 0042"],
        test_refs=["tests/services/test_phase_40_nm.py::test_query_path_2_hop"],
    ),
    Invariant(
        id=22, phase="P41", title="写入对称撤销",
        description="merge↔unmerge / archive↔reactivate",
        adr_refs=["ADR 0043"],
        test_refs=["tests/services/test_phase_41_fo.py::test_reactivate_memory_symmetric"],
    ),
    Invariant(
        id=23, phase="P44", title="扩展点 plugin registry 注册",
        description="核心代码不为特定 importer/provider 硬编",
        adr_refs=["ADR 0046"],
        test_refs=["tests/plugins/test_phase_44_pl.py::test_register_rejects_bad_plugin"],
    ),
    Invariant(
        id=24, phase="P45", title="时间敏感读 graph_clock",
        description="datetime.now 仅限内核",
        adr_refs=["ADR 0047"],
        test_refs=["tests/services/test_phase_45_gt.py::test_graph_clock_set_and_now"],
    ),
    Invariant(
        id=25, phase="P48", title="跨图谱出口 PII mask",
        description="联邦/导出必须支持 PII 脱敏 + visibility 过滤",
        adr_refs=["ADR 0050"],
        test_refs=["tests/services/test_phase_48_fs.py::test_server_masks_pii_in_response"],
    ),
    Invariant(
        id=26, phase="P51", title="世界对象必须有时间范围",
        description="effective_from / started_at 必填",
        adr_refs=["ADR 0053"],
        test_refs=["tests/services/test_phase_51_wm.py::test_world_objects_have_time_range"],
    ),
    Invariant(
        id=27, phase="P52", title="Agent 自主可解释",
        description="必须追溯到 drive / memory / trace",
        adr_refs=["ADR 0054"],
        test_refs=["tests/services/test_phase_52_ag.py::test_record_autonomous_action_requires_source"],
    ),
    Invariant(
        id=28, phase="P55", title="派生可从底层重建",
        description="persona_summary / narrative / insight / activation",
        adr_refs=["ADR 0057"],
        test_refs=["tests/services/test_phase_55_df.py::test_verify_insight_rebuildable"],
    ),
]


def get_all_invariants() -> list[Invariant]:
    return list(INVARIANTS)


def get_invariant(invariant_id: int) -> Invariant | None:
    for inv in INVARIANTS:
        if inv.id == invariant_id:
            return inv
    return None


def coverage_summary() -> dict:
    total = len(INVARIANTS)
    covered = sum(1 for i in INVARIANTS if i.test_refs)
    return {
        "total_invariants": total,
        "covered": covered,
        "uncovered": total - covered,
        "coverage_ratio": round(covered / total, 3) if total else 0.0,
        "uncovered_ids": [i.id for i in INVARIANTS if not i.test_refs],
    }


def list_as_dicts() -> list[dict]:
    return [i.to_dict() for i in INVARIANTS]
