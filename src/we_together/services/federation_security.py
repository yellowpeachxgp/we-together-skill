"""federation_security（Phase 48 FS）：Bearer token 鉴权 + rate limit + PII 脱敏。

- Bearer token：在 server 端检查 Authorization: Bearer <token>
- rate limit：per-token 每分钟 N 次
- PII 脱敏：email/phone 导出前自动 mask
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
import time
from dataclasses import dataclass, field


def generate_token() -> str:
    """生成 256-bit 随机 token。"""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token(provided: str, stored_hashes: list[str]) -> bool:
    h = hash_token(provided)
    return any(hmac.compare_digest(h, s) for s in stored_hashes)


# --- Rate limiter（内存；生产应 redis/kv） ---

@dataclass
class RateLimiter:
    max_per_minute: int = 60
    window_seconds: float = 60.0
    _buckets: dict[str, list[float]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.setdefault(key, [])
            bucket[:] = [t for t in bucket if now - t < self.window_seconds]
            if len(bucket) >= self.max_per_minute:
                return False
            bucket.append(now)
            return True

    def remaining(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key, [])
            bucket[:] = [t for t in bucket if now - t < self.window_seconds]
            return max(0, self.max_per_minute - len(bucket))


# --- PII 脱敏 ---

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\-\s]{7,}\d)(?!\d)")


def mask_email(text: str) -> str:
    def _m(m):
        name = m.group(1)
        domain = m.group(2)
        # 保留首字母 + 域名；中间 *
        head = name[0] if name else "*"
        return f"{head}***@{domain}"
    return EMAIL_RE.sub(_m, text)


def mask_phone(text: str) -> str:
    def _m(m):
        raw = m.group(1)
        digits_only = re.sub(r"\D", "", raw)
        if len(digits_only) < 7:
            return raw
        # 保留最后 4 位
        return "***" + digits_only[-4:]
    return PHONE_RE.sub(_m, text)


def mask_pii(text: str | None) -> str:
    if text is None:
        return ""
    return mask_phone(mask_email(text))


def sanitize_record(record: dict, *, fields: list[str] | None = None) -> dict:
    """对 dict 中指定字段做 mask_pii。默认针对 'summary' / 'primary_name' / 'note' / 'description'。"""
    fields = fields or ["summary", "primary_name", "note", "description", "metadata"]
    out = {}
    for k, v in record.items():
        if k in fields:
            if isinstance(v, str):
                out[k] = mask_pii(v)
            elif isinstance(v, dict):
                out[k] = {kk: mask_pii(vv) if isinstance(vv, str) else vv
                          for kk, vv in v.items()}
            else:
                out[k] = v
        else:
            out[k] = v
    return out


# --- Visibility policy ---

def is_exportable(record: dict) -> bool:
    """检查 record 是否允许导出。

    规则：
    - metadata.exportable=False 则不导出
    - visibility='private' 默认不导出
    - 否则可导出
    """
    meta = record.get("metadata") or {}
    if isinstance(meta, dict) and meta.get("exportable") is False:
        return False
    vis = record.get("visibility") or record.get("visibility_level")
    if vis == "private":
        return False
    return True
