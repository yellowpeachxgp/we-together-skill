# Codex 宿主验收矩阵

## 目标

用一组固定中文请求，验证 `we-together` skill family 的命中边界是否合理。

## 请求矩阵

### Router 应命中

- `看一下 we-together 当前状态`
- `读取 we-together 交接文档并继续推进`
- `帮我导入一段 we-together 材料`

### Dev 应命中

- `继续 we-together 的 Phase 72`
- `we-together 测试基线是多少`
- `读取 we-together 交接文档`

### Runtime 应命中

- `给我 we-together 图谱摘要`
- `查一下 we-together 的不变式`
- `查看 we-together 第 19 条不变式`

### Ingest 应命中

- `bootstrap we-together`
- `导入 narration 到 we-together`
- `导入 email 到 we-together`

### World 应命中

- `看一下 we-together tenant 状态`
- `查看 we-together active world`
- `继续 we-together 的 tenant/world isolation`

### Simulation 应命中

- `跑一下 we-together simulate_year`
- `做一个 we-together what-if`
- `给我 we-together dream_cycle insight`

### Release 应命中

- `跑一下 we-together release 自检`
- `验证 we-together skill 包`
- `给我 we-together 的 CHANGELOG 和 release notes`

### 不应命中

- `看一下当前状态`
- `ADR 是什么`
- `scene 是什么意思`
- `聊聊社会图谱理论`
- `帮我写个 Python 脚本`

## 验收规则

1. 强语义请求应落在正确 skill 家族
2. 裸词请求不应被 `we-together` 抢走
3. 任意目录启动时，skill 应优先依赖 `local-runtime.md`，而不是全盘搜索
4. 若需留档，使用 `scripts/capture_codex_skill_evidence.py` 记录命中证据
