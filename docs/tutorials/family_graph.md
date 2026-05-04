# 教程：给家庭成员建图谱

**场景**：让本地 we-together skill 记住家庭成员、关系、最近发生的事情，并能在一个 scene 里对话。

**时间**：15 分钟。默认使用 `mock` provider，不需要 API key。

## 1. 安装和初始化

```bash
git clone https://github.com/yellowpeachxgp/we-together-skill
cd we-together-skill
python -m venv .venv
source .venv/bin/activate
pip install -e .

.venv/bin/we-together bootstrap --root .
```

## 2. 导入一段家庭叙述

```bash
.venv/bin/python scripts/import_narration.py \
  --root . \
  --source-name "family-note" \
  --text "今晚爸爸做了他最拿手的糖醋排骨。妈妈说妹妹期末考了第一名，我们都很开心。"
```

导入会写入 raw evidence、event、memory、person/relation 候选和 patch 记录。随后看一下图谱：

```bash
.venv/bin/we-together graph-summary --root .
```

## 3. 创建一个家庭晚餐场景

如果你已经知道 person id，可以把他们作为 participant 放进 scene。下面的 id 只是示例；真实 id 以导入结果或数据库内容为准。

```bash
.venv/bin/python scripts/create_scene.py \
  --root . \
  --scene-type family_dinner \
  --summary "家庭晚餐后的近况聊天" \
  --participant p_dad \
  --participant p_mom \
  --participant p_me \
  --participant p_sis
```

命令会输出：

```json
{"scene_id": "<scene_id>"}
```

如果你只是想快速体验完整链路，也可以直接使用 demo 数据：

```bash
.venv/bin/we-together seed-demo --root .
.venv/bin/we-together graph-summary --root .
```

## 4. 跑一次对话

```bash
.venv/bin/python scripts/chat.py --root . --scene-id <scene_id>
```

进入 REPL 后输入：

```text
爸爸昨天做了什么菜？
```

这条路径会执行 retrieval -> SkillRequest -> mock/LLM response -> dialogue event -> inferred patches -> snapshot。

## 5. 打开 WebUI

```bash
.venv/bin/we-together webui --root .
```

浏览器打开：

```text
http://127.0.0.1:5173
```

WebUI 默认走 local skill bridge。浏览器不需要 token；provider token 属于本地 CLI 环境。

## 6. 看快照和图谱

```bash
.venv/bin/we-together snapshot list --root .
.venv/bin/we-together graph-summary --root .
.venv/bin/python scripts/dashboard.py --root . --port 7780
```

dashboard 打开：

```text
http://127.0.0.1:7780
```

## 7. 让图谱维护一轮

```bash
.venv/bin/we-together daily-maint --root . --skip-llm
.venv/bin/python scripts/simulate_week.py --root . --ticks 7 --budget 3 --archive
```

归档在 `benchmarks/tick_runs/*.json`。

## 8. 进阶

- `scripts/world_cli.py register-object --name "爸爸的乐高模型" --owner-id <person_id>`
- `scripts/world_cli.py register-place --name "家" --scope venue`
- `scripts/multi_agent_chat.py --root . --scene <scene_id> --turns 3`

## 9. 接入 Codex / Claude

- Codex: [`docs/hosts/codex.md`](../hosts/codex.md)
- Claude Code: [`docs/hosts/claude-code.md`](../hosts/claude-code.md)
- Claude Desktop: [`docs/hosts/claude-desktop.md`](../hosts/claude-desktop.md)
