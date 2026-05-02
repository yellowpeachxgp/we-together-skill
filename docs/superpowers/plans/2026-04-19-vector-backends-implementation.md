# Dual Vector Backends Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `sqlite_vec` 和 `faiss` 从 `VectorIndex` 的 stub backend 升级为真实可执行 backend，并把 bench / recall / 文档一起接上。

**Architecture:** 保持现有 SQLite BLOB schema 不变，在 `VectorIndex` 内部新增两条真实 backend 实现路径。`sqlite_vec` 走扩展 SQL 距离函数，`faiss` 走内存 `IndexFlatIP`，`flat_python` 继续作为稳定基线，`auto` 继续解析为 `flat_python`。

**Tech Stack:** Python 3.11+、SQLite、sqlite-vec（optional）、FAISS（optional）、pytest

---

### Task 1: 先写 backend 真路径测试

**Files:**
- Modify: `tests/services/test_phase_36_debt.py`
- Modify: `tests/services/test_phase_28_scale.py`
- Test: `tests/services/test_phase_36_debt.py`
- Test: `tests/services/test_phase_28_scale.py`

- [ ] **Step 1: 写 `sqlite_vec` / `faiss` 真路径的 failing tests**

```python
def test_vector_index_sqlite_vec_real_backend_with_fake_module(...):
    idx = VectorIndex.build(db, target="memory", backend="sqlite_vec")
    assert idx.backend == "sqlite_vec"
    assert idx.query(query_vec, k=1)[0][0] == "m1"


def test_vector_index_faiss_real_backend_with_fake_module(...):
    idx = VectorIndex.build(db, target="memory", backend="faiss")
    assert idx.backend == "faiss"
    assert idx.query(query_vec, k=1)[0][0] == "m1"
```

- [ ] **Step 2: 跑新增测试，确认当前实现红灯**

Run: `.venv/bin/python -m pytest tests/services/test_phase_36_debt.py tests/services/test_phase_28_scale.py -q`

Expected: FAIL，原因是当前 backend 仍返回 `sqlite_vec_fallback` / `faiss_fallback`，或没有真实查询路径。

- [ ] **Step 3: 增补 recall / bench 的接口测试**

```python
def test_associate_by_embedding_accepts_index_backend(...):
    result = associate_by_embedding(..., index_backend="flat_python")
    assert result["associated"] == ["m_flt"]


def test_bench_scale_accepts_backend_flag():
    parser = build_arg_parser()
    args = parser.parse_args(["--backend", "flat_python"])
    assert args.backend == "flat_python"
```

- [ ] **Step 4: 再跑相关测试，确认接口测试也先红灯**

Run: `.venv/bin/python -m pytest tests/services/test_phase_26_embedding.py tests/services/test_phase_36_debt.py -q`

Expected: FAIL，原因是 `associate_by_embedding()` 还没有 `index_backend` 参数，`bench_scale` 还没有 `--backend`。

- [ ] **Step 5: 提交前检查本任务只改测试**

Run: `git diff -- tests/services/test_phase_36_debt.py tests/services/test_phase_28_scale.py tests/services/test_phase_26_embedding.py scripts/bench_scale.py`

Expected: 只有测试和后续要改的接口入口被标记，无生产代码实现。

### Task 2: 实现 `VectorIndex` 双 backend

**Files:**
- Modify: `src/we_together/services/vector_index.py`
- Test: `tests/services/test_phase_36_debt.py`
- Test: `tests/services/test_phase_28_scale.py`

- [ ] **Step 1: 写最小实现骨架**

```python
@dataclass
class VectorIndex:
    target: str
    backend: str
    items: list[tuple[str, list[float]]] | None = None
    db_path: Path | None = None
    id_map: list[str] | None = None
    faiss_index: object | None = None
```

- [ ] **Step 2: 实现 `sqlite_vec` build/query**

```python
if resolved == "sqlite_vec":
    _require_sqlite_vec()
    return cls(target=target, backend="sqlite_vec", db_path=db_path)
```

```python
rows = conn.execute(
    f"SELECT {id_col} AS item_id, vec, vec_distance_cosine(vec, ?) AS distance "
    f"FROM {table} ORDER BY distance ASC LIMIT ?",
    (encode_vec(query_vec), k),
).fetchall()
```

- [ ] **Step 3: 实现 `faiss` build/query**

```python
faiss, np = _load_faiss_runtime()
index = faiss.IndexFlatIP(dim)
matrix = np.asarray(vectors, dtype="float32")
faiss.normalize_L2(matrix)
index.add(matrix)
```

```python
query = np.asarray([query_vec], dtype="float32")
faiss.normalize_L2(query)
scores, ids = self.faiss_index.search(query, k)
```

- [ ] **Step 4: 实现 hierarchical query 的 backend 分支**

```python
if backend == "sqlite_vec":
    ...
if backend == "faiss":
    ...
return cls.build(..., backend="flat_python").query(...)
```

- [ ] **Step 5: 跑 targeted tests 到绿灯**

Run: `.venv/bin/python -m pytest tests/services/test_phase_28_scale.py tests/services/test_phase_36_debt.py -q`

Expected: PASS

### Task 3: 接通 recall 与 benchmark

**Files:**
- Modify: `src/we_together/services/embedding_recall.py`
- Modify: `scripts/bench_scale.py`
- Test: `tests/services/test_phase_26_embedding.py`
- Test: `tests/services/test_phase_36_debt.py`

- [ ] **Step 1: 给 `associate_by_embedding()` 加 `index_backend` 参数**

```python
def associate_by_embedding(..., index_backend: str = "auto") -> dict:
    ...
```

- [ ] **Step 2: 无 filter 路径也改成统一走 `VectorIndex`**

```python
top = VectorIndex.build(
    db_path, target="memory", backend=index_backend,
).query(query_vec, k=top_k)
```

- [ ] **Step 3: 给 `bench_scale.py` 增加 `--backend`**

```python
ap.add_argument("--backend", default="flat_python")
...
idx = VectorIndex.build(db, target="memory", backend=args.backend)
report["backend"] = idx.backend
```

- [ ] **Step 4: 跑 recall/bench 相关测试**

Run: `.venv/bin/python -m pytest tests/services/test_phase_26_embedding.py tests/services/test_phase_36_debt.py tests/services/test_phase_53_qr.py -q`

Expected: PASS

- [ ] **Step 5: 手动跑一个 bench smoke**

Run: `.venv/bin/python scripts/bench_scale.py --root . --n 100 --queries 2 --backend flat_python`

Expected: 输出 JSON，包含 `backend` / `index_size` / `qps`。

### Task 4: 文档与回归

**Files:**
- Modify: `docs/CHANGELOG.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/superpowers/state/current-status.md`
- Test: `tests/services/test_phase_61_sp.py`

- [ ] **Step 1: 更新文档描述**

```md
- `VectorIndex` 的 `sqlite_vec` / `faiss` backend 已从 stub 升级为真 backend
- `auto` 仍保持 `flat_python`
```

- [ ] **Step 2: 跑向量相关测试全集**

Run: `.venv/bin/python -m pytest tests/services/test_phase_26_embedding.py tests/services/test_phase_28_scale.py tests/services/test_phase_36_debt.py tests/services/test_phase_47_sc.py tests/services/test_phase_53_qr.py tests/services/test_phase_61_sp.py -q`

Expected: PASS

- [ ] **Step 3: 跑全量回归**

Run: `.venv/bin/python -m pytest -q`

Expected: 全绿，passed 数在当前基线之上。

- [ ] **Step 4: 检查 diff 只包含本轮工作**

Run: `git diff -- src/we_together/services/vector_index.py src/we_together/services/embedding_recall.py scripts/bench_scale.py tests/services/test_phase_26_embedding.py tests/services/test_phase_28_scale.py tests/services/test_phase_36_debt.py docs/CHANGELOG.md docs/HANDOFF.md docs/superpowers/state/current-status.md`

Expected: 只包含本轮 backend/bench/doc 相关改动。

- [ ] **Step 5: 提交**

```bash
git add \
  src/we_together/services/vector_index.py \
  src/we_together/services/embedding_recall.py \
  scripts/bench_scale.py \
  tests/services/test_phase_26_embedding.py \
  tests/services/test_phase_28_scale.py \
  tests/services/test_phase_36_debt.py \
  docs/CHANGELOG.md \
  docs/HANDOFF.md \
  docs/superpowers/state/current-status.md \
  docs/superpowers/specs/2026-04-19-vector-backends-design.md \
  docs/superpowers/plans/2026-04-19-vector-backends-implementation.md
git commit -m "feat: real sqlite_vec and faiss vector backends"
```
