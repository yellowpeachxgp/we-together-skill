# 开发态提示

适用于：

- `看当前状态`
- `继续推进`
- `读交接文档`
- `继续某个 Phase`
- `检查 ADR / 不变式 / 基线`

执行顺序：

1. 读取 `references/local-runtime.md`
2. 直接使用其中的绝对路径读取：
   - `docs/HANDOFF.md`
   - `docs/superpowers/state/current-status.md`
3. 在需要代码上下文时，工作根目录直接定位到 `repo_root`
4. 对当前状态、下一步任务、测试基线给出简洁结论
5. 如果用户要求继续开发，再进入正常代码/测试流程

注意：

- 不要从 `~` 做全盘搜索，只在 `repo_root` 内工作
- 如果涉及 Phase、ADR、不变式，先读文档再读代码
