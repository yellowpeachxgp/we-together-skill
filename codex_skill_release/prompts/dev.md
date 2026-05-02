# release 开发态提示

适用于：

- `继续完善发布链路`
- `修 release 自检`
- `补 package/host smoke 回归`

执行顺序：

1. 读取 `references/local-runtime.md`
2. 先读 `HANDOFF.md` / `current-status.md` 中 release 与验证链路状态
3. 再看 `scripts/package_skill.py`、`verify_skill_package.py`、`skill_host_smoke.py`、`release_prep.py`
4. 对假阳性、证据缺口、发布材料给出结论或直接实现
