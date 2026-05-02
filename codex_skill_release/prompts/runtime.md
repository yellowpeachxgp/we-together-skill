# release 运行态提示

适用于：

- `打 skill 包`
- `验 skill 包`
- `跑 host smoke`
- `跑 release 自检`

优先入口：

- `scripts/package_skill.py`
- `scripts/verify_skill_package.py`
- `scripts/skill_host_smoke.py`
- `scripts/release_prep.py`

规则：

1. 先读 `references/local-runtime.md`
2. 一律优先复用现有 release CLI
3. 返回时带上产物路径、通过/失败项与关键证据
