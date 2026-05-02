# Release Notes — v0.15.0 (2026-04-19)

**Theme**: 消费就绪 + Tick 真归档 + 神经网格 + 遗忘/拆分 + 联邦 MVP

**Test baseline**: 521 passed (+44 over v0.14.0)
**ADR 总数**: 45
**Migrations**: 16
**不变式**: 22

## 三支柱达成度

| 支柱 | v0.14 | **v0.15** | 改进点 |
|------|:-----:|:---------:|-------|
| A 严格工程化 | 9.5 | **9.5** | 2 条新不变式（#21 / #22）|
| B 通用型 Skill | 8 | **9.5** | 三路宿主文档 + Dashboard + 联邦 MVP |
| C 数字赛博生态圈 | 7 | **8.5** | tick 归档 + 神经网格 + 遗忘 + 联邦 |

## 核心新能力

### 1. 消费就绪（5 分钟上手）
```bash
pip install -e .
python scripts/bootstrap.py --root .
python scripts/skill_host_smoke.py --root /tmp/smoke   # 4 步验收
python scripts/dashboard.py --port 7780                # 浏览器打开
```

### 2. 三路宿主接入
- `docs/hosts/claude-desktop.md`
- `docs/hosts/claude-code.md`
- `docs/hosts/openai-assistants.md`

### 3. Tick 真归档
```bash
python scripts/simulate_week.py --ticks 7 --budget 10 --archive
# 归档到 benchmarks/tick_runs/<ISO ts>.json
```

### 4. 神经网格 (vision 兑现)
```bash
python scripts/activation_path.py --from person_a --to person_b --max-hops 3
```
- migration `0016_activation_traces`
- record / multi_hop / plasticity / decay
- **不变式 #21**: 激活必须可 introspect

### 5. 遗忘 / 拆分 (对称可逆)
- `services/forgetting_service.archive_stale_memories` ↔ `reactivate_memory`
- `services/entity_unmerge_service.unmerge_person` (merged ↔ active)
- **不变式 #22**: 写入必须有对称撤销

### 6. 联邦 MVP
```bash
# 远端 skill B 启 server
python scripts/federation_http_server.py --root . --port 7781

# 本地 skill A 拉数据
from we_together.services.federation_client import FederationClient
c = FederationClient("http://b.example:7781")
persons = c.list_persons()
```

## 升级路径

```bash
git pull
.venv/bin/pip install -e .
.venv/bin/python scripts/bootstrap.py --root .   # migration 0016 自动补齐
```

**Breaking changes**: 无（SkillRequest/Response v1 冻结）。
**Bug fix**: `time_simulator._make_snapshot_after_tick` 之前 SQL 列名错被 try/except 吞；修后 snapshot 真写入。

## 不变式新增

- **#21** 任何激活传播机制必须可 introspect（能画出谁激活了谁、权重多少）
- **#22** 图谱写入必须有对称撤销（merge ↔ unmerge / archive ↔ reactivate / create ↔ mark_inactive）

## 留给 v0.16

- 真 LLM 跑 tick（需 key）→ 成本真实报告
- 真 sqlite-vec / FAISS 集成
- 联邦写路径 + 鉴权
- Claude Skills marketplace 真上架
- multi_agent_chat.py REPL
- contradiction → unmerge → patch 人工 gate workflow
- plugin / extension 机制
- i18n prompts

## 详细文档

- [Phase 38-43 mega-plan](superpowers/plans/2026-04-19-phase-38-43-mega-plan.md)
- [Phase 38-43 diff 报告](superpowers/state/2026-04-19-phase-38-43-diff.md)
- [Getting Started](getting-started.md)
- [Tick Scheduling](tick-scheduling.md)
- [Federation Protocol v1](superpowers/specs/federation-protocol-v1.md)
- ADR 0040 / 0041 / 0042 / 0043 / 0044 / 0045
