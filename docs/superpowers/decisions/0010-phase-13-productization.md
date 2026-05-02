# ADR 0010: Phase 13 — 产品化与 Onboarding

## 状态

Accepted — 2026-04-18

## 背景

v0.8.0 让能力面覆盖"图谱活化 / 宿主生态 / 真实数据 / 联邦 / 硬化"五方向，但仍是"开发者视角的 SDK"。`product-mandate.md` 第 B 条要求的"通用型 Skill 产品"需要：让非开发者能在分钟级从零跑起来。

## 决策

### D1. 统一 CLI 入口

`pyproject.scripts.we-together = we_together.cli:main`，子命令 dispatch 到 `scripts/*.py`。20+ 个既有脚本无需重写，只通过 SCRIPT_MAP 暴露。pip install -e . 后 `we-together` 命令立即可用。

### D2. Docker 部署走多阶段 + compose

`docker/Dockerfile` builder/runtime 两阶段保持 slim。`docker-compose.yml` 一次起 app + metrics:9100 + branch-console:8765 三服务，共享 `wt-data` volume。

### D3. Onboarding 以状态机实现

`services/onboarding_flow.py` 定义 5 步状态机（WELCOME → IMPORT_CHOICE → IMPORT_EXEC → SCENE_SETUP → FIRST_TURN → DONE）。纯函数 `next_step(state, answer)` 让 CLI / Web UI / AI agent 都能复用。`scripts/onboard.py` 是最薄 CLI 壳子，支持 `--dry-run`。

### D4. Demo 分两类宿主

`examples/claude-code-skill/` 含 Claude Code 专版 `SKILL.md` + `use_cases.md`；`examples/feishu-bot/` 是 stdlib http webhook server + 签名校验中间件。两个 demo 都可以独立运行。

### D5. Quickstart 文档优先

`docs/quickstart.md` 遵循"5 分钟从零到跑"原则：7 步（装 → init → seed → timeline → turn → snapshot → what-if）+ 常见问题。

## 后果

### 正面

- 非开发者可 10 分钟完成第一次使用
- pip 包 + Docker 双部署路径
- 两个真实宿主（Claude Code / 飞书）demo 可被复制

### 负面 / 权衡

- 飞书 bot 示例只是 echo，未接 chat_service.run_turn（避免测试期真实 LLM 依赖）
- Docker 构建未验证（本地无 Docker 守护进程），仅保证 Dockerfile 语法正确
- Onboarding 未接真实 ingest，留 state 供上层集成

### 后续

- Phase 14 eval 跑通后，`onboard` 的 IMPORT_EXEC 步可接入真实 importer
- Phase 17 what-if teaser 落地后，quickstart 第 7 步会激活
