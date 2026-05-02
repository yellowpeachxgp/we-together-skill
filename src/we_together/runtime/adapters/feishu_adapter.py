"""飞书（Lark）机器人 adapter：把 webhook 消息转换为 SkillRequest 形状。

飞书消息 webhook 简化 payload（我们只解析核心字段，其余透传到 metadata）:
  {
    "event_id": "...",
    "event_type": "im.message.receive_v1",
    "message": {"content": "...", "msg_type": "text"},
    "sender": {"user_id": "...", "name": "..."}
  }

对于响应（回帖）：adapter.format_reply 返回平台层要发的 JSON。
为了无人值守，保持纯转换函数，不做真实 HTTP 调用。
签名校验见 verify_signature（HMAC-SHA256 over timestamp+nonce+body）。
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any

from we_together.runtime.skill_runtime import SkillRequest, SkillResponse


def parse_webhook_payload(
    raw: dict, *, scene_id: str, system_prompt: str = "you are we-together bot",
) -> SkillRequest:
    msg = raw.get("message", {}) or {}
    sender = raw.get("sender", {}) or {}
    content_raw = msg.get("content", "")
    # 飞书 content 是 JSON 字符串 {"text":"..."}；兼容直接纯文本
    text = content_raw
    if isinstance(content_raw, dict):
        text = content_raw.get("text", "")
    elif isinstance(content_raw, str) and content_raw.startswith("{"):
        import json
        try:
            text = json.loads(content_raw).get("text", content_raw)
        except Exception:
            text = content_raw
    return SkillRequest(
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": text}],
        retrieval_package={},
        scene_id=scene_id,
        user_input=text,
        metadata={
            "adapter": "feishu",
            "event_id": raw.get("event_id"),
            "event_type": raw.get("event_type"),
            "sender_user_id": sender.get("user_id"),
            "sender_name": sender.get("name"),
        },
    )


def format_reply(response: SkillResponse, *, chat_id: str) -> dict:
    return {
        "chat_id": chat_id,
        "msg_type": "text",
        "content": {"text": response.text},
    }


def verify_signature(
    *, secret: str, timestamp: str, nonce: str, body: bytes, signature: str,
) -> bool:
    mac = hmac.new(
        secret.encode("utf-8"),
        msg=(timestamp + nonce).encode("utf-8") + body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(mac, signature)


class FeishuSkillAdapter:
    name = "feishu"

    def parse(self, raw: dict, *, scene_id: str) -> SkillRequest:
        return parse_webhook_payload(raw, scene_id=scene_id)

    def format(self, response: SkillResponse, *, chat_id: str) -> dict:
        return format_reply(response, chat_id=chat_id)
