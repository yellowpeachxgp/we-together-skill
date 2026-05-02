# Local Runtime

安装脚本会把这个模板渲染成 `local-runtime.md`，写入当前机器上的：

- `repo_root`
- `mcp_server_name`
- `preferred_language`
- `handoff_path`
- `current_status_path`

源模板仅用于说明，实际运行时请读取安装后生成的 `local-runtime.md`。

## 使用规则

1. skill 激活后第一步必须读 `local-runtime.md`
2. 不要自己从 `~` 做大范围搜索来猜项目路径
3. 如果 `local-runtime.md` 缺失或路径失效，应该提示先重新安装或更新本地 Codex skill，而不是默默降级
