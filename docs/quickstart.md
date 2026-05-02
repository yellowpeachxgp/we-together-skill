# Quickstart

> 适用于 we-together-skill v0.19.0。目标是在 5 分钟内跑起一个可对话的小社会图谱。

## 0. 环境

- Python 3.11+
- Node.js 仅在开发 WebUI 时需要
- 默认 LLM provider 是 `mock`，不需要 API key

## 1. 安装

```bash
git clone https://github.com/yellowpeach/we-together-skill
cd we-together-skill
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

确认：

```bash
.venv/bin/we-together version
```

期望：

```text
we-together 0.19.0
```

## 2. 初始化 + demo 数据

```bash
.venv/bin/we-together bootstrap --root ./data
.venv/bin/we-together seed-demo --root ./data
.venv/bin/we-together graph-summary --root ./data
```

demo 数据应包含 8 个 person、8 条 relation 和 3 个 active scene。具体 scene id 会由 seed 输出或 summary/DB 查询得到。

## 3. 跑一次交互式对话

```bash
.venv/bin/we-together chat --root ./data --scene-id <scene_id>
```

进入 REPL 后输入一句中文，例如：

```text
你好，请根据当前场景回应一轮。
```

系统会走 retrieval -> LLM/mock -> event -> patch -> snapshot。

## 4. 打开 WebUI

```bash
.venv/bin/we-together webui --root ./data
```

浏览器打开：

```text
http://127.0.0.1:5173
```

默认 WebUI 对话走本地 skill bridge，不需要 WebUI token。如果 `./data` 里没有 scene，先 seed demo 或导入材料。

## 5. 查看和维护

```bash
.venv/bin/we-together snapshot list --root ./data
.venv/bin/we-together daily-maint --root ./data --skip-llm
.venv/bin/we-together what-if --root ./data --scene-id <scene_id> --hypothesis "Bob 换团队"
```

如果你已经有一轮外部生成的回复，想把它写入图谱，可用：

```bash
.venv/bin/we-together dialogue-turn \
  --root ./data \
  --scene-id <scene_id> \
  --user-input "你好" \
  --response-text "你好，我在当前场景里。"
```

## 6. Codex skill family

```bash
.venv/bin/python scripts/install_codex_skill.py --family --force
.venv/bin/python scripts/validate_codex_skill.py --installed --family --skill-dir ~/.codex/skills
```

然后在交互式 Codex 中显式询问：

```text
看一下 we-together 当前状态
查一下 we-together 的不变式
给我 we-together 图谱摘要
```

## 常见问题

### 没有 LLM API key 怎么办？

直接使用默认 `mock`。真实 provider 是高级模式。

### bootstrap 之后为什么 WebUI 没法对话？

bootstrap 只创建 schema 和基础 seeds，不一定创建 active scene。请运行 `seed-demo`、`create-scene` 或导入材料。

### 多租户怎么跑？

```bash
.venv/bin/we-together seed-demo --root ./data --tenant-id alpha
.venv/bin/we-together webui --root ./data --tenant-id alpha
```

数据位于：

```text
./data/tenants/alpha/db/main.sqlite3
```

## 下一步阅读

- [Wiki 使用方法](wiki/usage.md)
- [Wiki 架构总览](wiki/architecture.md)
- [能力边界](wiki/capabilities.md)
- [交互流程](wiki/interaction-flows.md)
