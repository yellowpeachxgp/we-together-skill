# 飞书机器人 示例

把 we-together-skill 作为飞书机器人的后端：飞书 webhook → feishu_adapter → SkillRequest → `chat_service.run_turn` → 真实对话 + 图谱演化 → 回帖。

## 启动

```bash
we-together bootstrap --root ~/.we-together
we-together seed-demo --root ~/.we-together   # 或用 onboard 自定义
# 假设某个 work_discussion scene_id = scene_abcd

# mock provider（离线）
python examples/feishu-bot/server.py --root ~/.we-together --scene-id scene_abcd --port 7000

# 真 LLM
export WE_TOGETHER_LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python examples/feishu-bot/server.py --root ~/.we-together --scene-id scene_abcd
```

启动日志会显示：

```
feishu webhook on http://127.0.0.1:7000  (signing=off, llm_provider=mock)
```

## 反向代理（开发时）

```bash
ngrok http 7000
# 把 https URL + "/" 填到飞书开放平台的事件订阅
```

## 签名验证

```bash
export FEISHU_SIGNING_SECRET=xxxxxxxxxx
python examples/feishu-bot/server.py --root ~/.we-together --scene-id scene_abcd
```

## 行为

收到消息后：

1. 走 `parse_webhook_payload` 提取 `user_input`
2. 调 `chat_service.run_turn` → retrieval → SkillRequest → LLM → dialogue_event + patch
3. 把 response 作为 `text` 回帖

**每次对话都会推动图谱演化**（记忆新增 / persona drift / relation drift 等）。

## 错误处理

- `chat_service` 抛异常 → 回帖 `[we-together error] <msg>`
- LLM 没产出文本 → 回帖 `[we-together] 收到但未产出回复`
- 签名校验失败（设置了 `FEISHU_SIGNING_SECRET` 时）→ 401

## 支持的事件

- `url_verification`（飞书首次订阅握手）
- `im.message.receive_v1`（用户消息）

## 扩展方向

- 多 scene 路由：按 chat_id 映射不同 `scene_id`
- 接 `branch-console` 的 HITL 界面
- 加 `rbac_service` 限制某些敏感消息只对特定 role 处理
