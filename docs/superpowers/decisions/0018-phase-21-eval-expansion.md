# ADR 0018: Phase 21 — Eval 扩展

## 状态

Accepted — 2026-04-19

## 背景

Phase 14 只覆盖 relation 推理的 eval。Phase 21 把 memory condenser / persona drift 两个 LLM-驱动的演化子系统也纳入 eval，同时扩容 benchmark 套件。

## 决策

### D1. Condenser eval 走 LLM-as-judge

`eval/condenser_eval.run_condense_eval(benchmark_path, llm_client)`：
- 读 benchmark JSON `{cases: [{sources, condensed, expected_fidelity_min}]}`
- 每条 case 调 `judge_fidelity(sources, condensed)` 得 fidelity_score
- score >= expected_min 视为 passed，最终报 `pass_rate`

### D2. Persona drift eval 同框架

`eval/persona_drift_eval.run_persona_drift_eval`：把生成 persona 当作 summary、事件序列当作 sources 走 judge。调用者显式传 `generated_persona_by_case: dict[case_id, persona_text]`。

### D3. Benchmark 套件扩容（4 个新 benchmark）

- `condense_groundtruth.json` — 2 case
- `persona_drift_groundtruth.json` — 1 case
- `society_d_groundtruth.json` — 10 人基础（未来 seed_society_d 对齐）
- `society_work_groundtruth.json` — 纯同事 4 人场景

每个 benchmark 都必须有 `benchmark_name` 字段，供 `load_groundtruth` 校验。

### D4. Eval 结果形状统一

所有 eval 函数返回 `{benchmark, total, passed, pass_rate, cases}`（或 precision/recall/f1 等）。便于未来 eval 聚合器（Phase 22）。

## 后果

### 正面
- 核心 LLM 子系统有了"质量可测"的客观信号
- Benchmark 套件扩容让 seed_demo 之外的社会形态能被验证
- Eval 全链路依然 mock 兼容，无网络依赖

### 负面 / 权衡
- LLM-as-judge 本身的可信度依赖 judge 模型，可能与人类标注差距
- condense / persona benchmark 目前 case 量少（2 + 1），需要逐步扩充

### 后续
- Phase 22：benchmark 扩 10+ case 并引入版本号
- Eval 报告聚合器：一次跑所有 benchmark + 网页报告
