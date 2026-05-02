"""飞书机器人 webhook server (stdlib 实现)。

接收飞书 event webhook，经 feishu_adapter 转换为 SkillRequest，
调 chat_service.run_turn 做真实对话演化，回帖 LLM 回复。

启动:
  python examples/feishu-bot/server.py --root ~/.we-together --scene-id <scene_id>
  # 反向代理（ngrok）指向 http://127.0.0.1:7000

环境变量:
  FEISHU_SIGNING_SECRET  飞书签名密钥（可选；设置后启用验签）
  WE_TOGETHER_LLM_PROVIDER  mock / anthropic / openai_compat
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# 让脚本能找到源码
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from we_together.llm import get_llm_client
from we_together.runtime.adapters.feishu_adapter import (
    format_reply,
    parse_webhook_payload,
    verify_signature,
)
from we_together.runtime.skill_runtime import SkillResponse
from we_together.services.chat_service import run_turn


def _make_handler(*, db_path: Path, scene_id: str, secret: str | None):
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            if secret:
                ts = self.headers.get("X-Lark-Request-Timestamp", "")
                nonce = self.headers.get("X-Lark-Request-Nonce", "")
                sig = self.headers.get("X-Lark-Signature", "")
                if not verify_signature(secret=secret, timestamp=ts, nonce=nonce,
                                         body=body, signature=sig):
                    self.send_response(401); self.end_headers()
                    self.wfile.write(b'{"error":"signature"}')
                    return

            try:
                raw = json.loads(body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self.send_response(400); self.end_headers()
                return

            # URL verification challenge
            if raw.get("type") == "url_verification":
                resp = {"challenge": raw.get("challenge", "")}
                self._send(200, resp)
                return

            req = parse_webhook_payload(raw, scene_id=scene_id)
            # 真绑 chat_service.run_turn
            try:
                turn = run_turn(
                    db_path=db_path,
                    scene_id=scene_id,
                    user_input=req.user_input,
                    llm_client=get_llm_client(),
                    adapter_name="openai_compat",
                )
                reply_text = turn.get("text") or turn.get("response_text") or ""
                if not reply_text:
                    reply_text = "[we-together] 收到但未产出回复"
            except Exception as exc:
                reply_text = f"[we-together error] {exc}"

            resp = SkillResponse(text=reply_text, speaker_person_id=None)
            chat_id = (raw.get("message") or {}).get("chat_id", "")
            self._send(200, format_reply(resp, chat_id=chat_id))

        def _send(self, code: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a, **kw):
            pass
    return H


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--scene-id", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7000)
    args = ap.parse_args()
    db_path = Path(args.root).resolve() / "db" / "main.sqlite3"
    secret = os.environ.get("FEISHU_SIGNING_SECRET")
    provider = os.environ.get("WE_TOGETHER_LLM_PROVIDER", "mock")

    srv = HTTPServer(
        (args.host, args.port),
        _make_handler(db_path=db_path, scene_id=args.scene_id, secret=secret),
    )
    print(f"feishu webhook on http://{args.host}:{args.port}  "
          f"(signing={'on' if secret else 'off'}, llm_provider={provider})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
