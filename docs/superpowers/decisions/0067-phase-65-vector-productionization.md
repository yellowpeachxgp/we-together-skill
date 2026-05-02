---
adr: 0067
title: Phase 65 — 向量生产化
status: Accepted
date: 2026-04-19
---

# ADR 0067: Phase 65 — 向量生产化

## 状态
Accepted — 2026-04-19

## 背景

上一提交已经把 `VectorIndex(backend='sqlite_vec'|'faiss')` 从 stub 升级为真 backend，但还停留在“代码能跑”的层级，尚未进入“可发布、可复现、可归档”的生产化状态。主要缺口有三类：

1. **安装缺口**：`pyproject.toml` 没有原生向量依赖分组，用户无法通过标准 extras 一次装齐。
2. **证据缺口**：`bench_scale.py` 只能打印一次性 JSON，不能像 `simulate_week.py` / `simulate_year.py` 一样稳定归档。
3. **集成缺口**：虽然 fake-runtime tests 已覆盖真实代码路径，但还缺“环境装了真库时直接跑”的 integration tests。

这不满足 A 支柱的“严格工程化”：功能有了，但发布、验证、复现和证据链还不完整。

## 决策

### D1. 新增 `vector` optional extra

在 `pyproject.toml` 中新增：

- `sqlite-vec`
- `faiss-cpu`
- `numpy`

这样安装路径变成：

```bash
pip install -e .[vector]
```

而不是靠操作者自己记忆三条 pip 命令。

### D2. `bench_scale.py` 进入“可归档脚本”层级

新增：

- `build_report(...)`
- `archive_report(...)`
- `--archive`
- `--archive-dir`

归档文件名采用：

```text
bench_<n_label>_<backend>_<timestamp>.json
```

例如：

- `bench_50_sqlite_vec_2026-04-19T10-05-59Z.json`
- `bench_50_faiss_2026-04-19T10-05-59Z.json`

归档 payload 必须显式包含：

- `backend`
- `platform`
- `python_version`
- `generated_at`

### D3. 真库 integration tests 作为生产化门槛

新增两类测试：

- `sqlite_vec` installed → 真实建索引 + 查询
- `faiss` + `numpy` installed → 真实建索引 + 查询

若环境未安装，测试 `skip`；若已安装，则必须真跑，不再只依赖 fake runtime。

### D4. `auto` 语义保持不变

虽然真 backend 已经存在，本阶段仍保持：

```python
auto -> flat_python
```

原因：

- 行为不能随“本地是否装了 native 库” silently 漂移。
- benchmark、CI、release、用户复现都需要显式 backend 选择。

## 版本锚点

- 安装：`pyproject.toml` 新增 `vector` extra
- bench：`scripts/bench_scale.py` 支持 archive + metadata
- tests：新增 `tests/packaging/test_phase_65_vp_packaging.py`
- tests：新增 `tests/services/test_phase_65_vp.py`
- 本地基线：**699 passed, 4 skipped**

## 非目标（留给后续 phase）

- 100k / 1M 三 backend 真归档对比（Phase 66）
- nightly / CI 的 native backend smoke lane
- 根据 benchmark 自动切 backend
- `vec0` 虚表或 schema 迁移

## 拒绝的备选

### 备选 A：继续只靠手工 `pip install`

拒绝原因：不满足“可发布、可复现”的工程标准。

### 备选 B：只做 benchmark archive，不做真库 integration tests

拒绝原因：archive 只能证明脚本输出，不证明 runtime 在真实库上可用。

### 备选 C：让 `auto` 自动选择真 backend

拒绝原因：环境依赖漂移会破坏可预测性，不利于 CI 与回归审计。

## 下一步

1. 给 nightly 增加 vector smoke lane。
2. 做 `100k / 1M` compare benchmark 归档。
3. 把 benchmark 归档纳入 v0.19 release evidence。
