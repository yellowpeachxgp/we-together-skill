# crontab 调度示例

## 目标
让 `simulate_week.py` 每晚 02:00 跑一次 tick，归档报告到 `benchmarks/tick_runs/`。

## 安装

```bash
# 编辑 crontab
crontab -e

# 加入
0 2 * * * cd /path/to/we-together && \
  .venv/bin/python scripts/simulate_week.py --ticks 1 --budget 5 \
  > logs/tick_$(date +\%Y\%m\%d).log 2>&1
```

注意：
- 用 `.venv/bin/python` 避免 PATH 问题
- `%` 在 crontab 需 `\%` 转义
- 保证 `logs/` 目录存在

## k8s CronJob 版

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: wetogether-tick
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: tick
            image: python:3.11
            command:
            - python
            - /app/scripts/simulate_week.py
            - --root
            - /data
            - --ticks
            - "1"
            - --budget
            - "5"
          restartPolicy: OnFailure
```

## NATS 触发版（事件驱动，非日历驱动）

```python
# scripts/nats_trigger_tick.py（示例）
import asyncio, json, subprocess, sys
from nats.aio.client import Client as NATS

async def main():
    nc = NATS()
    await nc.connect("nats://localhost:4222")
    async def handler(msg):
        subject = msg.subject
        subprocess.run([sys.executable, "scripts/simulate_week.py",
                         "--ticks", "1", "--budget", "3"])
    await nc.subscribe("we_together.tick.request", cb=handler)
    await asyncio.Event().wait()

asyncio.run(main())
```

配合 `event_bus_service.NATSBackend` 发布 `tick.request` 即可驱动。

## 归档布局

```
benchmarks/tick_runs/
  2026-04-19T02:00:00Z.json    # 单日 tick 报告
  2026-04-20T02:00:00Z.json
  ...
```

每份 JSON 含 `simulate()` 返回 + `tick_sanity.evaluate()` 结果（Phase 39 落地）。
