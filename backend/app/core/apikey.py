"""AI 工具 API Key 的生成、哈希与解析。

明钥格式：`hpf_<prefix>_<random_secret>`，形如 `hpf_ab12cd_9f3k...`。
- 数据库只存 `key_hash`（HMAC-SHA256）与 `prefix`（用于展示/审计标识）
- 明钥仅在创建时返回一次，之后无法再取回
"""

import hashlib
import hmac
import re
import secrets

from app.config import settings

API_KEY_PREFIX = "hpf"
KEY_PATTERN = re.compile(rf"^{API_KEY_PREFIX}_([a-z0-9]{{6}})_([a-f0-9]{{64}})$")


def _hmac(value: str) -> str:
    return hmac.new(
        settings.secret_key.encode(), value.encode(), hashlib.sha256
    ).hexdigest()


def generate_api_key(user_id: int) -> tuple[str, str, str]:
    """生成一组 (明钥, prefix, key_hash)。"""
    prefix = secrets.token_hex(3)
    secret = secrets.token_hex(32)
    raw = f"{API_KEY_PREFIX}_{prefix}_{secret}"
    return raw, prefix, _hmac(raw)


def validate_api_key(raw: str) -> str | None:
    """校验明钥格式，返回其 key_hash（用于数据库比对）；格式非法返回 None。"""
    if not KEY_PATTERN.match(raw):
        return None
    return _hmac(raw)