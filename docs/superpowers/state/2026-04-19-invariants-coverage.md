# Invariants Coverage Report（v0.18.0）

**总数**：28 条不变式
**覆盖率**：100%（每条至少 1 个强制测试）
**不变式 #29（本期新增）**：**纸面不变式禁止**——每条不变式必须有 >= 1 个覆盖测试。

## 总览

```bash
python scripts/invariants_check.py summary
python scripts/invariants_check.py show 26
python scripts/invariants_check.py list
```

## 覆盖表

| # | Phase | 标题 | ADR | Test Ref |
|---|-------|------|-----|----------|
| 1 | P1 | 事件优先 | ADR 0001 | tests/services/test_patch_application.py::test_apply_patch_record_can_create_memory |
| 2 | P1 | 局部分支 | ADR 0001 | tests/services/test_branch_resolver.py::test_resolver_runs |
| 3 | P1 | 默认自动化+底层可逆 | ADR 0001 | tests/services/test_identity_fusion.py::test_score_basic |
| 4 | P1 | 摘要是派生视图 | ADR 0001 | tests/services/test_phase_55_df.py::test_get_insight_sources_returns_source_memory_ids |
| 5 | P1 | Skill-first 通用型 | ADR 0019 | tests/runtime/test_phase_33_skill_host.py::test_adapters_equivalent_payload_structure |
| 6 | P8-12 | retrieval_package 版本化 | ADR 0019 | tests/runtime/test_retrieval_package.py::test_build_basic |
| 7 | P8-12 | Skill 双路径 | ADR 0023 | tests/runtime/test_adapters.py::test_claude_adapter_build |
| 8 | P8-12 | bootstrap 幂等 | ADR 0019 | tests/db/test_bootstrap.py::test_bootstrap_is_idempotent |
| 9 | P13-17 | state 可衰减 | ADR 0016 | tests/services/test_state_decay.py::test_decay_linear_policy |
| 10 | P13-17 | relation 漂移 smallstep | ADR 0016 | tests/services/test_relation_drift.py::test_drift_window_limits |
| 11 | P18-21 | importer 输出契约 | ADR 0019 | tests/importers/test_real_world_importers.py::test_imessage_importer_reads_candidates |
| 12 | P18-21 | snapshot 可回滚 | ADR 0016 | tests/services/test_snapshot_service.py::test_rollback_removes_later_patches |
| 13 | P22-24 | graph_serializer JSON | ADR 0020/0023 | tests/services/test_phase_22_interop.py::test_canonical_roundtrip |
| 14 | P22-24 | narrative 派生可重建 | ADR 0022 | tests/services/test_phase_55_df.py::test_verify_narrative_arcs_rebuildable_missing |
| 15 | P25-27 | LLM 走 Mock + 延迟 import | ADR 0027 | tests/services/test_phase_36_debt.py::test_llm_providers_delayed_import |
| 16 | P25-27 | 向量 BLOB + 纯 Python | ADR 0027 | tests/services/test_phase_26_embedding.py::test_encode_decode_roundtrip |
| 17 | P29 | 多 agent 共享底层图谱 | ADR 0033 | tests/services/test_phase_29_30_31_32.py::test_person_agent_from_db |
| 18 | P30 | 主动写入预算+偏好 | ADR 0033 | tests/services/test_phase_29_30_31_32.py::test_check_budget_limits |
| 19 | P33 | SkillRuntime schema 版本化 | ADR 0034 | tests/runtime/test_phase_33_skill_host.py::test_skill_request_rejects_wrong_version |
| 20 | P34 | tick 可回滚 | ADR 0036 | tests/services/test_phase_39_ct.py::test_simulate_writes_real_snapshots |
| 21 | P40 | 激活可 introspect | ADR 0042 | tests/services/test_phase_40_nm.py::test_query_path_2_hop |
| 22 | P41 | 写入对称撤销 | ADR 0043 | tests/services/test_phase_41_fo.py::test_reactivate_memory_symmetric |
| 23 | P44 | plugin registry 注册 | ADR 0046 | tests/plugins/test_phase_44_pl.py::test_register_rejects_bad_plugin |
| 24 | P45 | graph_clock 优先 | ADR 0047 | tests/services/test_phase_45_gt.py::test_graph_clock_set_and_now |
| 25 | P48 | 跨图谱出口 PII mask | ADR 0050 | tests/services/test_phase_48_fs.py::test_server_masks_pii_in_response |
| 26 | P51 | 世界对象时间范围 | ADR 0053 | tests/services/test_phase_51_wm.py::test_world_objects_have_time_range |
| 27 | P52 | Agent 自主可解释 | ADR 0054 | tests/services/test_phase_52_ag.py::test_record_autonomous_action_requires_source |
| 28 | P55 | 派生可重建 | ADR 0057 | tests/services/test_phase_55_df.py::test_verify_insight_rebuildable |

## Meta-Tests

- `tests/invariants/test_phase_58_in.py::test_every_invariant_has_at_least_one_test_ref` 保证每条都有绑定
- `test_test_refs_point_to_existing_files` 校验测试文件真实存在
- `test_coverage_summary_100_percent` 断言覆盖率 1.0

## 不变式 #29

任何新不变式加入 `src/we_together/invariants.py` 时，必须：
1. `test_refs` 至少一个
2. 所指测试文件真实存在
3. 所指测试在 pytest 里真实运行（不 skip）

CI 会运行 `tests/invariants/test_phase_58_in.py` 自动拦截违规。

## 维护

增加 / 修改不变式时：
1. 更新 `src/we_together/invariants.py` 的 `INVARIANTS` list
2. 确保 test_refs 挂上
3. 相关 ADR 里标 synthesis
4. 跑 `pytest tests/invariants/` 全绿
