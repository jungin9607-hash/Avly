"""세션(소유 토큰)과 영상 서명 URL.

로그인이 없으므로 사고를 만들 때 발급한 session_id 를 아는 사람만 그 사고를 볼 수 있다.
브라우저의 <video src> 는 헤더를 보낼 수 없으므로 영상은 짧게 유효한 서명 URL 로 제공한다.
"""

import hashlib
import hmac
import time
from uuid import UUID

from fastapi import Header

from app.config import settings
from app.errors import AppError


def session_id(x_session_id: str | None = Header(default=None)) -> UUID:
    """요청 헤더 X-Session-Id 를 읽는다. 없거나 형식이 틀리면 401."""
    if not x_session_id:
        raise AppError(401, "SESSION_REQUIRED", "X-Session-Id 헤더가 필요합니다.")
    try:
        return UUID(x_session_id)
    except ValueError:
        raise AppError(401, "SESSION_INVALID", "X-Session-Id 형식이 올바르지 않습니다.") from None


def _signature(payload: str) -> str:
    return hmac.new(settings.app_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]


def sign_media(accident_id: UUID, kind: str, ttl: int | None = None, now: float | None = None) -> tuple[str, int]:
    expires = int((now if now is not None else time.time()) + (ttl or settings.media_url_ttl_seconds))
    payload = f"{accident_id}.{kind}.{expires}"
    return f"{payload}.{_signature(payload)}", expires


def verify_media(token: str, now: float | None = None) -> tuple[UUID, str]:
    """유효한 토큰이면 (accident_id, kind) 를 돌려준다. 아니면 403."""
    try:
        accident, kind, expires, signature = token.split(".")
        payload = f"{accident}.{kind}.{expires}"
        valid = hmac.compare_digest(signature, _signature(payload)) and int(expires) >= (now if now is not None else time.time())
        if valid:
            return UUID(accident), kind
    except (ValueError, TypeError):
        pass
    raise AppError(403, "MEDIA_LINK_INVALID", "영상 주소가 올바르지 않거나 만료되었습니다.")
