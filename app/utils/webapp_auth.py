"""Telegram WebApp `initData` HMAC-SHA256 tekshiruvi.

Spec: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any
from urllib.parse import parse_qsl

from core.config import settings

logger = logging.getLogger(__name__)

_MAX_AGE_SECONDS = 24 * 60 * 60  # initData 24 soat davomida yaroqli


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def parse_init_data(raw: str, *, max_age: int = _MAX_AGE_SECONDS) -> dict[str, Any] | None:
    """`initData` querystring'ini tekshiradi va lug'atga aylantiradi.

    Xato holatda `None` qaytaradi (auth_date muddat, imzo mos emas va h.k.).
    """
    if not raw:
        return None
    try:
        pairs = dict(parse_qsl(raw, keep_blank_values=True, strict_parsing=True))
    except ValueError:
        return None

    provided_hash = pairs.pop("hash", None)
    if not provided_hash:
        return None

    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret = _secret_key(settings.BOT_TOKEN)
    computed = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, provided_hash):
        return None

    auth_date_raw = pairs.get("auth_date")
    if auth_date_raw:
        try:
            auth_date = int(auth_date_raw)
        except ValueError:
            return None
        if time.time() - auth_date > max_age:
            return None

    if "user" in pairs:
        try:
            pairs["user"] = json.loads(pairs["user"])
        except json.JSONDecodeError:
            return None

    return pairs


def extract_telegram_id(init_data: str) -> int | None:
    parsed = parse_init_data(init_data)
    if parsed is None:
        return None
    user = parsed.get("user")
    if not isinstance(user, dict):
        return None
    tg_id = user.get("id")
    return int(tg_id) if tg_id is not None else None
