# Scale Bench Report (v0.18.0)

**Date**: 2026-04-19
**Phase**: 59 / ADR 0063
**Target**: 首次真跑 10k / 50k 规模压测并归档证据。

## Baseline（flat_python backend，MacBook）

| 规模 | dim | seed (s) | build (s) | per-query (ms) | QPS |
|-----:|----:|--------:|---------:|--------------:|----:|
| 10,000 | 16 | 0.072 | 0.009 | 15.23 | 65.6 |
| 50,000 | 16 | 0.438 | 0.041 | 78.88 | 12.7 |

归档文件：
- `benchmarks/scale/bench_10k_2026-04-18T21-26-47Z.json`
- `benchmarks/scale/bench_50k_2026-04-18T22-02-13Z.json`

## 观察

1. **flat_python backend 够用到 10k**（QPS 65.6，p50 ~15ms）
2. **50k 开始显著变慢**（QPS 12.7，p50 ~78ms）——符合 O(N) 预期
3. **真 100k / 1M 需要 sqlite-vec 或 FAISS**（v0.17 stub 已就位，真接留 v0.19）
4. **build_s 几乎可忽略**（50k < 50ms）——说明瓶颈在 query 的 cosine 计算

## 真正 bottleneck 分析

在 50k 规模下：
- 每 query 要做 50,000 次 cosine（纯 Python）
- ~78ms / 50k = 1.6 μs / cosine
- 接近 Python 解释器极限

## 下一步（v0.19+）

- 真接 sqlite-vec extension（已有延迟 import stub）→ 预期 QPS > 1000
- 真接 FAISS → 预期 QPS > 5000
- hierarchical_query 实测扩容到 50k
- 10k 规模下**连续 100 query 不降速**（检测内存 leak）

## 复现

```bash
rm -rf /tmp/wt_scale_repro && python scripts/bootstrap.py --root /tmp/wt_scale_repro
python scripts/bench_scale.py --root /tmp/wt_scale_repro --n 10000 --dim 16 --queries 50
python scripts/bench_scale.py --root /tmp/wt_scale_repro --n 50000 --dim 16 --queries 30
```

## 验收

- 测试 `test_phase_61_sp.py` 读取本目录归档，校验格式
- 违反（格式崩坏）→ CI 红
