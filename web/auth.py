import hmac
import hashlib
import time
from typing import Optional
from fastapi import Request, HTTPException, status  # type: ignore
from fastapi.responses import RedirectResponse  # type: ignore

from config.settings import settings
from database.queries import verify_admin_credentials

SESSION_COOKIE_NAME = "admin_session"
SESSION_DURATION_SECONDS = 7 * 24 * 3600  # 7 days


def create_session_token(username: str) -> str:
    """Generate tamper-proof signed session token: username:timestamp:signature."""
    ts = str(int(time.time()))
    payload = f"{username}:{ts}"
    sig = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"{payload}:{sig}"


def verify_session_token(token: Optional[str]) -> Optional[str]:
    """Verify signed session token and return username if valid and not expired."""
    if not token or ":" not in token:
        return None

    parts = token.split(":")
    if len(parts) != 3:
        return None

    username, ts_str, sig = parts
    payload = f"{username}:{ts_str}"
    expected_sig = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(sig, expected_sig):
        return None

    try:
        ts = int(ts_str)
        if time.time() - ts > SESSION_DURATION_SECONDS:
            return None
    except ValueError:
        return None

    return username


def get_current_admin(request: Request) -> Optional[str]:
    """Read session cookie and return username if authenticated."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    return verify_session_token(token)


class NotAuthenticatedException(Exception):
    """Exception raised when an unauthenticated request attempts to access an admin endpoint."""
    pass


def require_admin(request: Request) -> str:
    """Dependency that ensures user is authenticated, otherwise redirects to /admin/login."""
    user = get_current_admin(request)
    if not user:
        raise NotAuthenticatedException()
    return user
