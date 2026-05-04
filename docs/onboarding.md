# Onboarding 指南

`we-together-skill` 的第一次使用流程走这一条：

```bash
git clone https://github.com/yellowpeachxgp/we-together-skill
cd we-together-skill
pip install -e .              # 或 pip install we-together
we-together onboard --root ./mywe   # 交互式引导
```

或直接 dry-run 看看会跑什么：

```bash
we-together onboard --root ./mywe --dry-run
```

## 5 个步骤

1. **WELCOME** — 介绍 we-together
2. **IMPORT_CHOICE** — 选择首个数据源（narration / text_chat / email / skip）
3. **IMPORT_EXEC** — 执行导入（或 dry-run 时跳过）
4. **SCENE_SETUP** — 起第一个场景名
5. **FIRST_TURN** — 说第一句话给场景

完成后会给出后续建议命令（bootstrap / ingest / create-scene / graph-summary）。

## 环境变量

| 变量 | 含义 |
|---|---|
| `WE_TOGETHER_LLM_PROVIDER` | `mock` / `anthropic` / `openai_compat` |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | 真实 LLM 调用 |

## 跳过交互

如果你只想准备环境，不走引导：

```bash
we-together bootstrap --root ./mywe
we-together seed-demo --root ./mywe
we-together graph-summary --root ./mywe
```
