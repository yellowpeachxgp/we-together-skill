# ADR 0011: Phase 14 — 评估与质量

## 状态

Accepted — 2026-04-18

## 背景

281/288 passed 的单元测试只验证代码正确性，不验证图谱推理质量。持续演进需要 groundtruth + eval + 回归检测，否则看不出"LLM 输出质量是否下降"。

## 决策

### D1. 目录分工

- `benchmarks/`: groundtruth 数据（JSON）
- `src/we_together/eval/`: 加载、度量、推理、judge、regression
- `scripts/eval_relation.py`: CLI 入口

### D2. schema 与契约

groundtruth JSON schema: `{benchmark_name, persons, expected_relations, expected_scenes}`。`GroundtruthSet` dataclass 提供 `relation_pairs()` 规范化为 `(a, b, core_type)` 三元组集合。

### D3. metrics 纯函数

`compute_precision_recall_f1(predicted, groundtruth)` 不依赖任何上下文。所有 eval 模块都使用它。

### D4. LLM-as-judge 可选

`eval/llm_judge.py` 提供忠实度打分，输入源材料 + 摘要，输出 `{fidelity_score, missing_points, fabrications}`。走 `LLMClient.chat_json`，mock-friendly。

### D5. Baseline + 回归

`eval/regression.py`:
- `save_baseline` / `load_baseline`
- `detect_regression(current, baseline, tolerance=0.05)` 对 precision/recall/f1 检查
- CLI `--save-baseline` 写首版；`--baseline <path>` 激活回归检测，回归时 exit 3

### D6. Society C benchmark 作为首个 groundtruth

`benchmarks/society_c_groundtruth.json`：8 人 / 4 期望关系 / 3 期望场景。作为首个回归锚。

## 后果

### 正面
- 任何改动都可通过 `eval-relation` 量化影响
- Judge 给记忆凝练 / persona drift 一个 LLM-based 质量信号
- CI 可以把 eval 纳入门禁

### 负面 / 权衡
- groundtruth 依赖人工维护；规模扩大后需要 crowd-sourcing
- 当前 `_fetch_predicted_relations` 只看 event_targets→relation 的 participants，不完全覆盖 direct relations 表

### 后续
- Phase 14 延伸：memory condenser / persona drift 也加专门 benchmark
- Phase 14 延伸：把 eval 接入 CI yaml，PR 回归自动评论
