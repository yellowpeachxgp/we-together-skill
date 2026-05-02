# Good First Issues

v0.19 本地收口后阶段开放给新贡献者的"入门任务"清单。难度从低到高。

## 🟢 15 分钟级（文档 / 小 bug）

1. **补 tutorial**: `docs/tutorials/` 新增一份（读书会 / DevOps 团队 / 项目组图谱）
2. **翻译**: 把 `CONTRIBUTING.md` / `CODE_OF_CONDUCT.md` 补英文版
3. **补 script --help**: 任何 `scripts/*.py` 缺详细 help 的补上
4. **修 typo**: CHANGELOG / ADR / README 里的错字
5. **补 comparisons**: `docs/comparisons/vs_X.md` 写一个新框架（Letta / MemGPT / Dify）
6. **补 example plugin**: `examples/` 加一个更完整的 plugin（Hook 示例）

## 🟡 1-2 小时级（小功能）

7. **新 importer plugin**: Slack / Discord / Notion（见 plugins/authoring.md）
8. **新 CLI 命令**: 如 `scripts/person_timeline.py --person X`
9. **benchmark 扩展**: 跑一份 `bench_scale.py --backend all --n 10000` compare 归档
10. **测试补充**: 某个 service 覆盖 <90%，补 property-based 测试

## 🔴 半天级（中等）

11. **tenant CLI 收尾**: 为剩余确实需要 tenant 的脚本补 `--tenant-id`
12. **federation 写路径扩展**: 补 `422/429` 之外的更多 curl smoke
13. **i18n 扩展**: 加法语 / 西语 / 韩语 prompt variant
14. **persona_drift learning**: agent_drives + persona_facets 真联动
15. **unmerge gate follow-up**: 补 target validation / tenant CLI 测试 / operator UX（post-v0.19 local slice）

## ⚫ 多天级（大）

16. **multi_agent_chat 交互式**: 人类真 stdin 加入作为第 N 个 agent
17. **mkdocs-material 集成**: 优化文档站点 UI + 部署到 GitHub Pages
18. **1M+ compare 报告深化**: 把 `bench_compare_*` 做成更完整的趋势报告
19. **agent task decomposition**: multi-agent 协作完成一个 multi-step goal
20. **新 importer: 飞书 / 钉钉**

## 选题指南

找到合适的 issue 后：
1. **评论**"I'd like to work on this"（防撞车）
2. 提 **draft PR** 早期分享思路
3. 参考 [ADR 目录](superpowers/decisions/) 看相关决策
4. 参考 [Service Inventory](superpowers/state/2026-04-19-service-inventory.md) 避免重复造轮子
5. 新增代码必须通过全量 pytest + 不违反当前不变式注册表

## 导师

维护者会在 24 小时内回应 issue。重度重构先在 issue 讨论，不要直接写几千行代码过来。
