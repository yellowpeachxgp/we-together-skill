---
name: we-together
description: "把一群人（同事/朋友/家人/伙伴）蒸馏成一个可对话、可演化的小型社会图谱 Skill。"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
---

# we-together skill (Claude Code 使用版)

这是 `we-together-skill` 针对 **Claude Code** 宿主场景定制的 skill 说明。

## 用前准备

```bash
pip install -e /path/to/we-together-skill
we-together bootstrap --root ~/.we-together
we-together seed-demo --root ~/.we-together
```

## 3 个典型用例

### ① 引导一次"跟小社会对话"

```bash
we-together graph-summary --root ~/.we-together
we-together build-pkg --root ~/.we-together --scene-id <scene_id>
we-together dialogue-turn --root ~/.we-together --scene-id <scene_id> --input "今天谁最开心？"
```

### ② 导入真实数据（iMessage 示例）

```bash
we-together ingest narration --root ~/.we-together --text "小张和小李周末去爬山"
we-together daily-maint --root ~/.we-together
```

### ③ 时间线回顾（Phase 15 能力）

```bash
we-together timeline --root ~/.we-together --person-id <pid>
we-together build-pkg --root ~/.we-together --scene-id <scene_id> --as-of 2025-12-01
```

## 设计哲学

- **Skill-first**：所有能力都通过 `we-together <subcommand>` 暴露，不需要 Claude Code 额外插件
- **图谱演化**：每次对话会自动推导 patch、写 snapshot、失效 cache
- **可回滚**：`we-together snapshot rollback --target <snap_id>`

## 相关文档

- `docs/onboarding.md`
- `docs/CHANGELOG.md`
- `docs/superpowers/state/current-status.md`
