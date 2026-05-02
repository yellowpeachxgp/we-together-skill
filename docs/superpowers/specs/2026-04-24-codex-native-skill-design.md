# Codex Native we-together Skill Design

> **状态**：Implemented locally — 2026-04-25
> **目的**：把 `we-together` 从“仓库内 SKILL.md + MCP server”升级成“可安装到 Codex 本地技能目录、支持中文平衡触发、具备完整安装与验证链路的原生 skill 家族”。

## 1. 背景

当前仓库已经具备三块关键基础：

1. 项目级 [`SKILL.md`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/SKILL.md)
2. 可用的 [`scripts/mcp_server.py`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/scripts/mcp_server.py)
3. 成熟的项目状态文档体系：
   - [`docs/HANDOFF.md`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/docs/HANDOFF.md)
   - [`docs/superpowers/state/current-status.md`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/docs/superpowers/state/current-status.md)

这说明 `we-together` 已经具备：

- 项目自描述能力
- MCP 运行时接线能力
- 长工作流交接能力

但这仍然不能满足用户真正想要的体验：

- 在 Codex 交互界面里，直接用中文自然语言输入
- 不必每次手动提示 MCP server 名称
- 不必每次先手动切换到项目目录
- 让 Codex 更像是在“自动进入 we-together skill”，而不是“碰巧用了一次工具”

因此本次设计不是继续堆工具，而是增加一层 **Codex 原生本地 skill 包装层**，让 `we-together` 变成一个可安装、可更新、可验证、可触发的完整 skill。

## 2. 问题定义

现状存在四类体验断层。

### 2.1 只有 MCP，没有 Codex 原生 skill

当前 `we-together-local-validate` 是一个可调用的 MCP server，但它依然表现为：

- 一个可用工具
- 而不是一个会被 Codex 交互式语义路由自动优先命中的原生 skill

### 2.2 没有明确的中文触发边界

用户想要的是“我随便说中文关键词，Codex 就能自动进入这套 skill 语境”。
现在缺的不是功能，而是：

- 触发词体系
- 触发与非触发边界
- 面向 Codex 的 `description` 设计

### 2.3 当前目录耦合仍然明显

虽然 MCP 工具调用本身不依赖当前目录，但以下动作仍然强依赖 `cwd`：

- 读交接文档
- 继续开发
- 跑测试
- 执行仓库脚本

当 Codex 从 `~` 启动时，它会：

1. 先在家目录里搜索
2. 再猜测仓库位置
3. 再慢慢定位到项目

这会导致进入成本偏高。

### 2.4 缺少安装 / 更新 / 校验闭环

当前还没有标准化命令去完成：

- 安装到 `~/.codex/skills/`
- 覆盖更新
- 校验 skill 结构
- 校验本机路径注入
- 校验 MCP 注册

因此 skill 目前“有代码”，但还不算“完整工程化可用”。

## 3. 设计目标

### G1. 平衡触发

自动触发策略采用“平衡”模式：

- 只在请求明显与 `we-together` 项目本身相关时触发
- 或请求明显与 `we-together` 运行时能力相关时触发
- 不抢普通中文问题

### G2. 中文优先

面向用户的触发词、解释、skill 入口说明，以中文优先设计。
英文只保留最低必要兼容。

### G3. 任意目录可进入 skill 语境

不要求用户必须先 `cd` 到仓库目录。
skill 安装后，应通过安装时生成的本机运行时资料快速得到：

- `repo_root`
- `mcp_server_name`
- 关键文档绝对路径

### G4. 复用现有能力

不新造第二套运行时。
继续复用现有：

- 项目文档
- 仓库脚本
- MCP server
- 测试体系

### G5. 工程化闭环

必须同时交付：

- Codex 原生 skill 包
- 安装脚本
- 更新脚本
- 校验脚本
- 自动化测试

## 4. 非目标

本次设计明确不做：

1. 不修改 Codex CLI 内部的真实路由机制
2. 不承诺“所有中文请求 100% 自动触发”
3. 不新增第二个 `we-together` MCP server
4. 不把整个仓库重构成纯 skill 仓库
5. 不在第一版就把所有潜在运行时切片都拆完；仅先落 `dev/runtime/ingest/world/simulation/release`

## 5. 用户故事

### U1. 查询当前状态

用户在任意目录启动 Codex 后输入：

`看一下 we-together 当前状态`

期望：

- 自动激活 `we-together` skill 语境
- 直接读 `HANDOFF.md` 和 `current-status.md`
- 给出状态摘要与下一步建议

### U2. 查询运行时不变式

用户输入：

`查一下这个 skill 的不变式`

期望：

- 自动激活 `we-together`
- 优先调用 MCP 工具
- 返回 invariants 数量与摘要

### U3. 查询图谱摘要

用户输入：

`给我图谱摘要`

期望：

- 自动激活 `we-together`
- 调用 `we_together_graph_summary`
- 返回 tenant 与计数
- 空图谱时说明为默认 tenant 空状态，而不是系统错误

### U4. 继续推进开发

用户输入：

`继续推进 Phase 72`

期望：

- 自动激活 `we-together`
- 先读状态文档
- 再进入代码、测试、实现语境

### U5. 导入材料

用户输入：

`帮我导入一段人物材料`

期望：

- 自动激活 `we-together`
- 不当作普通对话
- 直接进入导入态工作流

## 6. 参考仓库启发

参考：

- `titanwings/colleague-skill`
- `notdog1998/yourself-skill`

它们共同展示出一个“完整 skill 仓库”的典型形态：

- 根级 `SKILL.md`
- `prompts/`
- `tools/`
- 面向不同宿主的安装脚本
- 明确的触发词与执行根说明

相较之下，当前 `we-together` 仓库更像：

- 一个主项目
- 自带项目级 skill 文档
- 自带 MCP 运行时

所以本次设计不直接复刻对方仓库，而是抽取它们“完整工程化 skill”的优点，再适配 `we-together` 当前项目形态。

## 7. 方案比较

### 方案 A：轻量桥接版

只新增一个最小 Codex skill，把触发词写到 `description`，进入后转调现有 MCP。

优点：

- 成本低
- 落地快

缺点：

- 安装 / 更新 / 校验闭环不完整
- 长期扩展会乱
- 不像完整 skill 仓库

### 方案 B：完整总入口版

增加一个完整的 `codex_skill/` 目录，并补齐安装、更新、校验脚本。

优点：

- 最接近参考 skill 的工程化程度
- 结构清晰
- 复用现有项目运行时
- 易于后续扩展

缺点：

- 一次性新增文件较多
- 需要补测试和工具链

### 方案 C：多 skill 家族版

拆成：

- `we-together-router`
- `we-together-dev`
- `we-together-runtime`
- `we-together-ingest`

优点：

- 长期扩展性最强

缺点：

- 第一版太重
- 超出当前需求

**结论**：采用 **方案 B：完整总入口版**。

## 8. 最终结构

### 8.1 Skill 包目录

```text
codex_skill/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── prompts/
│   ├── dev.md
│   ├── runtime.md
│   └── ingest.md
└── references/
    ├── triggers.md
    └── local-runtime.template.md
```

### 8.2 支持模块与脚本

```text
src/we_together/packaging/
└── codex_skill_support.py

scripts/
├── install_codex_skill.py
├── update_codex_skill.py
└── validate_codex_skill.py

tests/packaging/
└── test_codex_skill_support.py
```

## 9. 触发策略设计

### 9.1 触发层次

#### 强触发

- `we-together`
- `社会图谱`
- `数字人项目`
- `记忆图谱`
- `当前状态`
- `交接文档`
- `不变式`
- `ADR`
- `图谱摘要`
- `导入材料`
- `继续 Phase`

#### 运行态次触发

- `graph summary`
- `scene`
- `memory`
- `relation`
- `tenant`
- `查 invariants`
- `查 self describe`

#### 明确不触发

- 泛化社会图谱理论
- 与本项目无关的其他仓库开发
- 没有 `we-together` 项目语义的普通编程问题

### 9.2 平衡模式定义

“平衡”不是尽可能多地抓请求，而是：

- 强绑定仓库名和项目能力词
- 明确排除无关语义
- 让用户在多数相关中文请求中都能命中
- 但不为了提高命中率而牺牲边界

因此 `SKILL.md` 的 `description` 字段必须同时包含：

1. 触发范围
2. 中文示例
3. 非触发边界

## 10. 运行模式分流

### 10.1 开发态

适用请求：

- 当前状态
- 交接文档
- 继续推进
- Phase / ADR / 不变式 / 基线

行为：

- 先读 `local-runtime.md`
- 直接用其中的绝对路径读关键文档
- 再切入代码和测试

### 10.2 运行态

适用请求：

- 图谱摘要
- 不变式列表
- invariant 详情
- self describe

行为：

- 先读 `local-runtime.md`
- 再走 MCP
- 不先扫源码

### 10.3 导入态

适用请求：

- 导入 narration / file / email / directory
- bootstrap
- 初始化图谱

行为：

- 在 `repo_root` 中直接调现有仓库脚本
- 执行后返回图谱摘要或建议

## 11. 本机路径注入设计

### 11.1 原因

如果 skill 从 `~` 被触发，而没有本机路径注入，Codex 需要：

1. 搜索整个家目录
2. 猜测仓库位置
3. 再进入项目

这既慢也不稳定。

### 11.2 安装时生成内容

在安装后的 skill 目录里生成：

- `references/local-runtime.md`
- `references/local-runtime.json`

### 11.3 注入字段

- `repo_root`
- `mcp_server_name`
- `preferred_language = zh-CN`
- `handoff_path`
- `current_status_path`

### 11.4 读取规则

Skill 激活后第一步必须读取 `references/local-runtime.md`。

这条规则是“任意目录可进入项目语境”的核心。

## 12. 安装 / 更新 / 校验设计

### 12.1 安装脚本

`scripts/install_codex_skill.py`

职责：

- 校验源目录结构
- 拷贝 skill 到 `~/.codex/skills/we-together`
- 生成本机运行时资料

### 12.2 更新脚本

`scripts/update_codex_skill.py`

职责：

- 走 force-install
- 仓库更新后覆盖本地 skill

### 12.3 校验脚本

`scripts/validate_codex_skill.py`

职责：

- 校验源 skill 结构
- 校验安装后结构
- 校验是否生成 `local-runtime.*`
- 校验 Codex config 中是否注册了目标 MCP server

## 13. 复用原则

本次设计只做入口包装，不做第二套运行时。

继续复用：

- [`scripts/mcp_server.py`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/scripts/mcp_server.py)
- [`docs/HANDOFF.md`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/docs/HANDOFF.md)
- [`current-status.md`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/docs/superpowers/state/current-status.md)
- 现有导入脚本
- 现有测试基线

## 14. 风险与缓解

### R1. 触发词太激进

风险：

- 抢普通问题

缓解：

- 平衡模式
- 明确写非触发边界
- 单独维护 `references/triggers.md`

### R2. 安装后仓库路径失效

风险：

- 用户移动仓库目录后，`repo_root` 过期

缓解：

- 提供 `update_codex_skill.py`
- 校验脚本检查路径存在性

### R3. MCP server 名称漂移

风险：

- 正文硬编码名称后，配置变化导致失效

缓解：

- 不在 skill 正文中写死 server 名称
- 安装时写入 `local-runtime.*`

### R4. 只有安装，没有验证

风险：

- 本地 skill 装上了，但结构坏了

缓解：

- 安装脚本
- 更新脚本
- 校验脚本
- 测试

## 15. 验收标准

### 功能验收

安装后，在任意目录的 Codex 交互窗口中，以下请求应高概率自动进入 `we-together` skill：

- `看一下 we-together 当前状态`
- `读取交接文档并继续推进`
- `查一下这个 skill 的不变式`
- `给我图谱摘要`
- `帮我导入一段人物材料`
- `继续 Phase 72`

### 工程验收

必须同时满足：

1. 安装脚本可运行
2. 更新脚本可运行
3. 校验脚本可运行
4. 对应测试通过
5. 安装后的 skill 目录可被 Codex 识别

## 16. 后续演进

本次完成后，后续可继续扩展：

1. 拆分成 `runtime / dev / ingest / world / simulation` 子 skill
2. 补更强的中文触发矩阵
3. 增加其他宿主目录安装器
4. 增加面向 world / tenant / simulation 的专项 prompt

第一版先收敛到“完整总入口型 Codex native skill”。
