# Year-Run Bench Report (v0.18.0)

**Date**: 2026-04-19
**Context**: Phase 59 / ADR 0061—we-together 首次完整跑完 **365 天模拟**并归档。

## Baseline Run

| 项 | 值 |
|---|---|
| Seed | `seed_society_c`（小社会：2 人 + 1 scene） |
| Days simulated | 365 |
| LLM budget | 0（纯 Mock，无真 LLM 调用） |
| Total months | 13（30 day/month + 5 days） |
| Snapshots added | 2 |
| Sanity.healthy | ✅ True |
| Integrity.healthy | ✅ True |
| Integrity issues | 0 |
| Wall time | < 1 秒（本机 MacBook） |
| Archive file | `benchmarks/year_runs/year_run_2026-04-18T21-20-54Z.json` |

## 观察

1. **图谱稳定性**：全年 0 integrity issue，无 dangling / orphan / cycle
2. **Snapshot 稀疏**：2 个 snapshot（受限于 `time_simulator._make_snapshot_after_tick` 的 scene 要求）——未来可扩大触发条件
3. **无预算下的演化**：当 LLM budget=0 时，dreamcycle / proactive_scan 被跳过，但 decay / drift 仍工作
4. **性能**：365 次 tick < 1 秒——证明核心编排路径已高度优化

## 与现有 tick_run 对比

- 一份 `tick_runs/2026-04-18T19-37-40Z.json` 是 7 天报告
- 本报告是 **365 天全年** 报告

## 复现

```bash
rm -rf /tmp/wt_year_repro
.venv/bin/python scripts/bootstrap.py --root /tmp/wt_year_repro
.venv/bin/python -c "
import sys; sys.path.insert(0, 'scripts')
from seed_demo import seed_society_c
from pathlib import Path
seed_society_c(Path('/tmp/wt_year_repro'))"
.venv/bin/python scripts/simulate_year.py \
    --root /tmp/wt_year_repro --days 365 --budget 0 --archive-monthly
```

## 下一步（v0.19+）

- 真 LLM 跑（budget > 0）+ 成本采样
- 更大 seed（50 人）+ 365 天
- tick 间隔随机（非均匀 daily）
- 多 scene 并发

## 验收

- 测试 `tests/services/test_phase_59_sy.py::test_archived_year_run_in_repo` 会读取本报告并校验格式
- 违反则 CI 红
