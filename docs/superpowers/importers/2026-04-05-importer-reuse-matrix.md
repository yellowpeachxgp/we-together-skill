# Importer 复用矩阵与接入优先级

## 1. 文档目标

本文档用于把参考项目中的已有采集器与解析器能力映射到 `we together` 的统一 importer 体系中。

目标是回答：

- 哪些能力可以直接复用
- 哪些只能借鉴思路
- 哪些输入源是第一阶段优先接入的
- 哪些存在明显技术风险或依赖缺口

## 2. 复用策略

第一阶段不追求“完全重写所有 importer”。
优先策略是：

- 能包起来就先包
- 不能直接包就先保留兼容格式
- 真正重构 importer 适配层放在统一契约之下进行

## 3. 优先级总表

### P0：第一阶段优先接入

- 微信聊天导出 / 文本导出
- iMessage
- 飞书文档 / 消息
- 邮件
- 用户口述 / 粘贴文本

### P1：第二批接入

- 钉钉文档 / 消息
- Slack
- 图片 / 截图 OCR

### P2：后续接入

- QQ
- 社交媒体导出
- 更复杂的浏览器抓取路径

## 4. 参考项目复用矩阵

### 4.1 `titanwings/colleague-skill`

可直接优先复用：

- `tools/feishu_auto_collector.py`
- `tools/feishu_browser.py`
- `tools/feishu_mcp_client.py`
- `tools/dingtalk_auto_collector.py`
- `tools/slack_auto_collector.py`
- `tools/email_parser.py`

主要价值：

- 工作型数据源覆盖广
- 企业协作平台导入路径成熟
- 对工作人物面的抽取思路最清晰

风险：

- 多数工具直接面向“单人物 Skill 生成器”
- 输出格式需要被重新包进统一 `ImportResult`

### 4.2 `notdog1998/yourself-skill`

优先借鉴或兼容：

- `tools/wechat_parser.py`
- `tools/qq_parser.py`
- `tools/photo_analyzer.py`
- `tools/social_parser.py`

主要价值：

- 生活面与自我记忆面材料来源丰富
- 口述、自我描述、图片这类来源处理路径比较直接

风险：

- 某些解析器实现深度不足
- 部分格式声明大于真实实现

### 4.3 `titanwings/ex-skill`

优先复用：

- `tools/wechat_parser.py`
- `tools/wechat_decryptor.py`

主要价值：

- 微信 / iMessage 路径更硬核
- 对关系强度、冲突链、亲密互动事件识别思路最强

风险：

- 工具是围绕前任场景设计的
- 需要从“单关系人格”改造成“通用社会事件 importer”

## 5. 来源到统一 importer 的映射

### 5.1 微信

第一阶段建议支持两种入口：

- 文本导出入口
- 数据库解密后入口

优先复用来源：

- `ex-skill/tools/wechat_parser.py`
- `ex-skill/tools/wechat_decryptor.py`
- `yourself-skill/tools/wechat_parser.py` 作为弱兼容补充

### 5.2 iMessage

优先复用来源：

- `ex-skill/tools/wechat_parser.py` 中的 iMessage 路径

### 5.3 飞书

优先复用来源：

- `colleague-skill/tools/feishu_auto_collector.py`
- `colleague-skill/tools/feishu_browser.py`
- `colleague-skill/tools/feishu_mcp_client.py`

### 5.4 钉钉

优先复用来源：

- `colleague-skill/tools/dingtalk_auto_collector.py`

### 5.5 Slack

优先复用来源：

- `colleague-skill/tools/slack_auto_collector.py`

### 5.6 邮件

优先复用来源：

- `colleague-skill/tools/email_parser.py`

### 5.7 图片 / 截图

优先借鉴来源：

- `yourself-skill/tools/photo_analyzer.py`
- `yourself-skill/tools/social_parser.py`

### 5.8 口述 / 粘贴文本

这类输入不一定需要复杂 parser。
第一阶段可直接通过统一文本 importer 进入 `RawEvidence`。

## 6. 第一阶段推荐接入顺序

### 6.1 第一梯队

- 文本型聊天 importer
- iMessage importer
- 飞书 importer
- email importer
- text narration importer

理由：

- 最容易形成事件流
- 最容易验证 identity 融合
- 最容易验证运行时 scene 激活

### 6.2 第二梯队

- 钉钉 importer
- Slack importer
- image / screenshot importer

### 6.3 第三梯队

- QQ importer
- social export importer

## 7. 风险清单

### 7.1 权限风险

- 飞书 / 钉钉 / Slack 都依赖外部平台权限
- 微信数据库依赖本地环境与解密条件

### 7.2 格式漂移风险

- 上游工具支持的导出格式可能变化
- 文档里声明支持，不代表代码里真的完整支持

### 7.3 输出不一致风险

- 不同 importer 当前输出格式差异很大
- 必须统一封装到 `ImportResult`

## 8. 第一阶段最小可用 importer 集

如果只实现第一阶段最小可用集合，建议为：

- `text_chat_importer`
- `imessage_importer`
- `feishu_importer`
- `email_importer`
- `narration_importer`

这 5 个足以支撑：

- 人物构建
- 身份融合
- 关系推理
- 共享记忆生成
- 运行时场景验证

## 9. 下一步建议

在本文档之后，建议继续整理：

1. 每个 importer 的统一接口签名
2. 每个 importer 的 `ImportResult` 映射模板
3. 首版 importer 实现计划

## 10. 结论

第一阶段的 importer 工作不应从零乱写。

它应被推进为：

> **以参考项目为部件库、以统一契约为约束、按优先级逐步接入的 importer 复用工程。**
