"""Per-IP request limits for unauthenticated endpoints (login, invite, signup).

Works together with the per-account lock (5 failures → 15 min) so neither
password guessing on one account nor spraying across accounts is practical.
The key is the client address as seen by uvicorn, which only honours
X-Forwarded-For from the reverse proxy listed in --forwarded-allow-ips.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

LOGIN_LIMIT = "10/minute"
INVITE_LIMIT = "10/minute"
SIGNUP_LIMIT = "5/minute"

limiter = Limiter(key_func=get_remote_address, headers_enabled=False)
