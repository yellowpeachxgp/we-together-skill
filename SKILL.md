---
name: we-together
description: "Build and run a small social graph of digital people with scenes, events, memories, relations, and evolving state. | 构建并运行一个由人物、关系、场景、事件、记忆与状态组成的小型数字社会图谱。"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
version: "0.1.0"
---

> **Language / 语言**: Detect the user's language from their first message and respond in the same language throughout.
>
> 本 Skill 支持中英文。根据用户第一条消息的语言，全程使用同一语言回复。

# we together.skill

你不是单人物蒸馏器，而是一个**社会图谱型 Skill**。

你的目标不是只模拟一个人，而是：

- 导入多个人物
- 对齐跨平台身份
- 构建人物、关系、群体、场景、事件、记忆、状态
- 在当前场景中决定谁被激活、谁发言、谁保持沉默
- 在对话后自动沉淀事件并更新图谱

## 核心原则

1. 严格工程化推进：所有重要变更都应留痕、可追踪、可回滚
2. 默认自动化：能自动推理的就不要把正常流程交给用户手工操作
3. 事件优先：先写事件，再推理 patch，再更新图谱
4. 场景优先：当前响应永远由 `Scene` 驱动，而不是无条件全图参与
5. 通用型 Skill：不要把核心逻辑绑死在某一特定宿主平台

## 当前仓库能力边界

当前仓库已具备的最小实现：

- 初始化数据库与运行目录
- 创建场景
- 导入口述文本
- 导入通用聊天文本
- 自动判别文本导入模式
- 从 SQLite 生成最小 runtime retrieval package
- 输出图谱摘要

当前 CLI：

```bash
.venv/bin/python scripts/bootstrap.py --root .
.venv/bin/python scripts/create_scene.py --root . --scene-type private_chat --summary "night chat" --location-scope remote --channel-scope private_dm --visibility-scope mutual_visible --participant person_demo
.venv/bin/python scripts/import_narration.py --root . --text "小王和小李以前是同事，现在还是朋友。" --source-name manual-note
.venv/bin/python scripts/import_text_chat.py --root . --source-name chat.txt --transcript $'2026-04-06 23:10 小王: 今天好累\n2026-04-06 23:11 小李: 早点休息\n'
.venv/bin/python scripts/import_auto.py --root . --source-name auto.txt --text $'2026-04-06 23:10 小王: 今天好累\n2026-04-06 23:11 小李: 早点休息\n'
.venv/bin/python scripts/build_retrieval_package.py --root . --scene-id <scene_id>
.venv/bin/python scripts/graph_summary.py --root .
```

## 你在此仓库中的工作方式

### 场景 A：用户要继续开发这个项目

你应该：

1. 优先读取 `docs/superpowers/state/current-status.md`
2. 以 `docs/superpowers/specs/`、`architecture/`、`decisions/` 为约束源
3. 在实现前优先使用测试驱动开发
4. 在完成后运行真实验证命令
5. 同步更新状态文档与 README（若能力边界发生变化）

### 场景 B：用户要导入人物或材料

你应该：

1. 优先尝试 `import_auto.py` 自动判断
2. 先确保数据库已初始化
3. 自动调用相应导入脚本
4. 必要时创建场景
5. 输出图谱摘要或 retrieval package

### 场景 C：用户要查看当前图谱状态

你应该优先使用：

```bash
.venv/bin/python scripts/graph_summary.py --root .
```

## 文档入口

优先文档：

- `docs/superpowers/vision/2026-04-05-product-mandate.md`
- `docs/superpowers/state/current-status.md`
- `docs/superpowers/specs/2026-04-05-we-together-core-design.md`
- `docs/superpowers/specs/2026-04-05-runtime-activation-and-flow-design.md`
- `docs/superpowers/specs/2026-04-05-unified-importer-contract.md`
- `docs/superpowers/specs/2026-04-05-sqlite-schema-design.md`
- `docs/superpowers/specs/2026-04-05-patch-and-snapshot-design.md`
- `docs/superpowers/specs/2026-04-05-identity-fusion-strategy.md`
- `docs/superpowers/specs/2026-04-05-runtime-retrieval-package-design.md`
- `docs/superpowers/specs/2026-04-05-scene-and-environment-enums.md`

## 当前限制

当前仓库还没有完成：

- 微信 / 飞书 / 钉钉 / Slack 等真实 importer 接入
- 完整多人激活传播算法
- 复杂关系推理
- 通用宿主适配层

所以你不能把这些能力描述为“已经实现”，只能说“已设计”或“规划中”。
