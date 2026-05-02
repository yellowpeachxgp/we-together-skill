# scripts/ CLI 索引

本目录所有可执行 CLI 脚本一览。使用方式：`.venv/bin/python scripts/<name>.py --help`。

## 基础设施

| 脚本 | 用途 |
|---|---|
| `bootstrap.py` | 初始化项目目录、migrations、seeds |
| `lint.sh` | ruff + mypy 工程化检查 |
| `e2e_smoke.sh` | 端到端烟测 10 步链路 |

## 导入链

| 脚本 | 用途 |
|---|---|
| `import_narration.py` | 旁白文本导入 |
| `import_text_chat.py` | 结构化对话文本导入 |
| `import_email_file.py` | 单封 `.eml` 导入 |
| `import_directory.py` | 批量目录导入（.txt/.md/.eml） |
| `import_llm.py` | LLM 驱动的候选抽取（Phase 4+） |
| `import_wechat_text.py` / `import_wechat_csv.py` | 微信 CSV 原型 importer |

## Runtime 与对话

| 脚本 | 用途 |
|---|---|
| `create_scene.py` / `close_scene.py` / `archive_scene.py` | 场景生命周期 |
| `build_retrieval_package.py` | 构建 retrieval_package（支持 `--scene-id` / `--scenes` 多场景） |
| `record_dialogue.py` | 记录单条对话事件 |
| `dialogue_turn.py` | 一键端到端 turn |
| `chat.py` | 多人共演 REPL |
| `agent_chat.py` | Agent loop（tool_call/respond） |

## 演化与维护（daily_maintenance 涵盖）

| 脚本 | 用途 |
|---|---|
| `daily_maintenance.py` | 一次跑 6 步：drift / decay / auto_resolve / merge / persona_drift / memory_condense（`--skip-llm` 跳过 LLM） |
| `relation_drift.py` | 关系漂移 |
| `state_decay.py` | 状态衰减 |
| `auto_resolve_branches.py` | 分支自动解决 |
| `merge_duplicates.py` | 身份合并 |
| `extract_facets.py` | facet 抽取 |
| `condense_memories.py` | 记忆凝练（Phase 8） |
| `cold_memory.py` | 冷记忆 archive/list/restore（Phase 8） |

## Snapshot 与回滚

| 脚本 | 用途 |
|---|---|
| `snapshot.py` | `list` / `rollback` / `replay` 子命令 |
| `graph_summary.py` | 图谱快照摘要 |

## 联邦与观测（Phase 11-12）

| 脚本 | 用途 |
|---|---|
| `branch_console.py` | Branch 冲突裁决 HTTP 迷你控制台（bearer token） |
| `metrics_server.py` | Prometheus `/metrics` 端点 |
| `bench_large.py` | 大规模压测 + 冷/热检索延迟 p50/p95 |
| `package_skill.py` | `.weskill.zip` 打包 / 解包 |

## Phase 13-17 新增 CLI

| 脚本 | 用途 |
|---|---|
| `onboard.py` | 交互式 onboarding 引导（5 步）支持 `--dry-run` |
| `eval_relation.py` | 跑 relation 推理 eval；`--save-baseline` / `--baseline` 回归门禁 |
| `timeline.py` | 打印 person 的 persona_history / active_relations / recent_events |
| `relation_timeline.py` | 打印 relation 的 strength 时序（day/week/month bucket） |
| `what_if.py` | What-if 社会模拟 teaser（LLM 推演） |

统一入口：`we-together <subcommand>`（pip 安装后可用，见 `src/we_together/cli.py` 的 SCRIPT_MAP）

## 建议使用路径

- 新环境：`bootstrap.py` → `seed_demo.py` → `build_retrieval_package.py`
- 日常维护：`daily_maintenance.py`
- 长期运行：`metrics_server.py` + `bench_large.py` 常态化 + `cold_memory.py archive` 定期归档
