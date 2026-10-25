"""
Admin authentication for the research dashboard and data exports.

A single shared password (ADMIN_PASSWORD) is exchanged at /api/admin/login
for a short-lived bearer token: "<expiry>.<HMAC-SHA256(expiry)>", signed with
ADMIN_TOKEN_SECRET. Stateless, so nothing extra is stored in the database.

- ADMIN_PASSWORD unset  -> every admin endpoint answers 503 (admin disabled),
  so a deployment never exposes participant data by forgetting to set it.
- ADMIN_TOKEN_SECRET unset -> a random per-process secret is used; tokens
  then stop working on restart, which only means logging in again.
"""
import hashlib
import hmac
import os
import secrets
import time
from typing import Optional

from fastapi import Header, HTTPException

TOKEN_TTL_SECONDS = 8 * 60 * 60   # one working day of a lab session

_SECRET = (os.environ.get("ADMIN_TOKEN_SECRET") or secrets.token_hex(32)).encode()


def _admin_password() -> Optional[str]:
    return os.environ.get("ADMIN_PASSWORD") or None


def _sign(payload: str) -> str:
    return hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()


def check_password(password: str) -> bool:
    expected = _admin_password()
    if expected is None:
        raise HTTPException(503, "admin access is disabled: set ADMIN_PASSWORD on the server")
    return hmac.compare_digest(password.encode(), expected.encode())


def issue_token() -> str:
    expiry = str(int(time.time()) + TOKEN_TTL_SECONDS)
    return f"{expiry}.{_sign(expiry)}"


def _token_valid(token: str) -> bool:
    expiry, _, sig = token.partition(".")
    if not expiry.isdigit() or not hmac.compare_digest(sig, _sign(expiry)):
        return False
    return int(expiry) > time.time()


def require_admin(authorization: Optional[str] = Header(None)) -> None:
    """FastAPI dependency guarding every /api/admin/* data endpoint."""
    if _admin_password() is None:
        raise HTTPException(503, "admin access is disabled: set ADMIN_PASSWORD on the server")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not _token_valid(token.strip()):
        raise HTTPException(401, "admin login required")
