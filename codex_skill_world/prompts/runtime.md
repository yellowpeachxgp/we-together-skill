# world 运行态提示

适用于：

- `we-together tenant 状态`
- `we-together world 摘要`
- `查看对象/地点/项目`
- `active world`

优先入口：

- `scripts/world_cli.py active-world`
- `scripts/world_cli.py register-object`
- `scripts/world_cli.py register-place`
- `scripts/world_cli.py register-project`
- `src/we_together/services/world_service.py`

规则：

1. 先读 `references/local-runtime.md`
2. world 相关请求优先用 `repo_root` 下脚本与服务，不先全盘搜索
3. 返回时带上 tenant/world 维度，不把空 world 误报成异常
