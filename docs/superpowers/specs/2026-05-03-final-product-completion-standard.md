# we-together 最终产品完成标准

日期：2026-05-03
状态：Active completion gate

本文档定义“整个项目的大完成形态”。它不是某个阶段节点，也不是一次文档收口；它是后续所有开发、发布和商业化判断的门禁。

## 1. 产品完成定义

we-together 的完成形态是一个可开源、可本地执行、可商业化包装的 Skill-first 社会 + 世界图谱运行时。完成态必须同时满足：

- 用户能从空目录安装、初始化、导入或 seed、对话、查看图谱、查看事件/patch/snapshot、处理 operator review。
- CLI、MCP、Codex skill family、WebUI local bridge 和 `.weskill.zip` package 使用同一个本地优先运行时心智模型。
- 浏览器默认不持有 provider token；真实 provider token 属于 CLI/local runtime 环境。
- 关键写入遵守 event -> patch -> snapshot。
- 高风险歧义进入 local branch / operator review，不静默破坏图谱。
- 文档、README、Wiki、release checklist 和 self-audit 数字一致。
- 发布包不包含本地 DB、缓存、构建目录、密钥或宿主私有状态。

## 2. “0 bug”的工程定义

本项目不把“0 bug”写成不可验证口号。完成态的可执行定义是：

- 零已知 P0/P1/P2 缺陷。
- strict release gate 全绿。
- 全量 pytest 全绿，允许明确 skip。
- WebUI unit/build/visual gate 全绿。
- MCP fresh stdio self-describe / summary / scene / snapshot / run_turn / import smoke 全绿。
- package verify 全绿。
- 文档 stale scan 全绿。
- 安全和发布卫生检查无阻塞项。

如果发现新缺陷，缺陷必须进入以下路径之一：

- 修复并补测试。
- 明确降级为已知限制，并写入文档与 release note。
- 标记为发布阻塞，禁止声明完成。

## 3. 最终门禁命令

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/invariants_check.py summary
.venv/bin/python scripts/self_audit.py
.venv/bin/python scripts/release_strict_e2e.py --profile strict
cd webui && npm test -- --run
cd webui && npm run build
cd webui && npm run visual:check
git diff --check
```

发布到 PyPI 或 GitHub Release 前，还必须执行：

```bash
.venv/bin/python -m build --wheel --sdist
.venv/bin/python -m twine check \
  dist/we_together-<NEW_VERSION>-py3-none-any.whl \
  dist/we_together-<NEW_VERSION>.tar.gz
.venv/bin/python scripts/release_prep.py --version <NEW_VERSION>
```

## 4. 不可伪装为完成的事项

以下事项只有在有代码、测试、运行证据和文档后才能宣称完成：

- 真 provider 长周期运行质量。
- 所有真实世界 importer 的高保真生产级解析。
- 多用户云服务、RBAC、计费和托管 SaaS。
- PyPI / GitHub Release 已经实际发布。
- 商业 SLA、合规承诺和安全审计报告。

## 5. 当前推进策略

后续开发按缺口矩阵推进，而不是按单点功能自嗨：

1. 先修会阻塞开源安装、运行、打包、验证的 P0/P1。
2. 再补齐 first-run UX、operator cockpit、release evidence、示例资产。
3. 最后才推进真实 provider 长跑、商业化包装和生态扩展。
