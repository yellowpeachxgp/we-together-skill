# 使用方法

## 1. 本地安装

```bash
git clone https://github.com/yellowpeach/we-together-skill
cd we-together-skill
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

确认版本：

```bash
.venv/bin/we-together version
```

期望输出：

```text
we-together 0.19.0
```

## 2. 初始化 root

推荐把数据目录显式传给 `--root`：

```bash
.venv/bin/we-together bootstrap --root ./data
```

这会创建：

```text
data/db/main.sqlite3
```

如果使用当前仓库根目录作为 root：

```bash
.venv/bin/we-together bootstrap --root .
```

会使用：

```text
db/main.sqlite3
```

## 3. 快速灌入 demo 小社会

```bash
.venv/bin/we-together seed-demo --root ./data
.venv/bin/we-together graph-summary --root ./data
```

demo 通常包含：

- 8 个 person
- 8 条 relation
- 3 个 active scene
- 若干 memory / event / patch

如果不 seed，数据库可以是健康的，但没有 scene 时不能运行 scene-grounded 对话。

## 4. 跑一次 retrieval

先从 seed 输出或 scene list 中找到 scene id，然后：

```bash
.venv/bin/we-together build-pkg --root ./data --scene-id <scene_id>
```

retrieval package 会包含 scene summary、participants、active relations、relevant memories、current states、activation map、safety budget、recent changes 等字段。

## 5. 跑一次对话

```bash
.venv/bin/we-together chat --root ./data --scene-id <scene_id>
```

进入 REPL 后输入一句话。成功时会产生：

- `event_id`
- `snapshot_id`
- 推理出的 patch 数量

所有写入仍通过 event -> patch -> snapshot 链路。

如果你已经有外部回复文本，要把一轮对话写入图谱：

```bash
.venv/bin/we-together dialogue-turn \
  --root ./data \
  --scene-id <scene_id> \
  --user-input "你好" \
  --response-text "你好，我会根据当前场景回应。"
```

## 6. 启动 WebUI

```bash
.venv/bin/we-together webui --root ./data
```

默认启动：

- WebUI: `http://127.0.0.1:5173`
- local skill bridge: `http://127.0.0.1:7781`

浏览器默认通道不需要 WebUI token。WebUI 会：

1. 请求 `/api/runtime/status` 确认 local skill bridge。
2. 请求 `/api/scenes` 读取本地 active scenes。
3. 请求 `/api/summary` 读取本地 DB summary。
4. 请求 `/api/graph`、`/api/events`、`/api/patches`、`/api/snapshots`、`/api/world`、`/api/branches` 读取真实 cockpit 数据。
5. 对话时 POST `/api/chat/run-turn`。

如果 root 没有 scene，WebUI 会提示先 bootstrap + seed-demo 或导入材料，不会静默发送 demo scene id。
默认生产路径不会静默回落到 demo 数据。视觉开发需要 demo 数据时，显式使用 URL `?demo=1` 或设置浏览器 `localStorage.we_together_demo_mode=1`。

WebUI 空库起步可直接点：

- `Bootstrap`：初始化当前 root / tenant。
- `Seed demo`：写入 Society C 小社会。
- `Narration import`：从一段口述材料导入 event、person、relation、memory、snapshot。

Operator Review 中的确认操作会 POST `/api/branches/<branch_id>/resolve`，可附带 operator note；note 会作为 resolve `reason` 进入 patch payload。实际写入仍由 patch applier 执行，不由浏览器直接改 SQLite。

## 7. 使用 Codex skill family

安装：

```bash
.venv/bin/python scripts/install_codex_skill.py --family --force
```

校验：

```bash
.venv/bin/python scripts/validate_codex_skill.py --installed --family --skill-dir ~/.codex/skills
```

安装后本机有 7 个 skill：

- `we-together`
- `we-together-dev`
- `we-together-runtime`
- `we-together-ingest`
- `we-together-world`
- `we-together-simulation`
- `we-together-release`

推荐从交互式 Codex 使用，并在请求中显式带 `we-together` 语义：

```text
看一下 we-together 当前状态
查一下 we-together 的不变式
给我 we-together 图谱摘要
帮我导入一段 we-together 材料
继续 we-together 的 Phase 72
```

## 8. 常用验证

```bash
.venv/bin/python scripts/self_audit.py
.venv/bin/python scripts/invariants_check.py summary
.venv/bin/python -m pytest -q
.venv/bin/python scripts/release_strict_e2e.py --profile strict
```

WebUI 相关验证：

```bash
.venv/bin/python -m pytest tests/runtime/test_webui_host.py tests/runtime/test_webui_dev.py tests/runtime/test_webui_cli.py -q
cd webui
npm test -- --run
npm run build
npm run visual:check
```

本地 bridge 健康检查：

```bash
curl -s http://127.0.0.1:5173/api/runtime/status
curl -s http://127.0.0.1:5173/api/scenes
curl -s http://127.0.0.1:5173/api/summary
curl -s http://127.0.0.1:5173/api/graph
curl -s http://127.0.0.1:5173/api/world
curl -s http://127.0.0.1:5173/api/events?limit=5
curl -s http://127.0.0.1:5173/api/branches?status=open
```

`/api/graph` 当前覆盖 person / relation / memory / group / scene / state / object / place / project 节点；`/api/world` 覆盖 participants、objects、places、projects、agent_drives、autonomous_actions。

## 9. 多租户

默认 tenant：

```bash
.venv/bin/we-together seed-demo --root ./data
```

命名 tenant：

```bash
.venv/bin/we-together seed-demo --root ./data --tenant-id alpha
```

存储位置：

```text
./data/tenants/alpha/db/main.sqlite3
```

WebUI 也可指定 tenant：

```bash
.venv/bin/we-together webui --root ./data --tenant-id alpha
```
