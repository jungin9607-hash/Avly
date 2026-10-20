"""라우터가 공통으로 쓰는 의존성."""

from datetime import datetime, timezone
from functools import lru_cache
from uuid import UUID

from fastapi import Depends

from app.errors import AppError
from app.repository import Repository
from app.security import session_id


@lru_cache
def _repository() -> Repository:
    return Repository()


def get_repo() -> Repository:
    return _repository()


def ensure_not_expired(expires_at: datetime | None) -> None:
    """세션이 끝난 사고·분석은 정리 작업이 아직 돌지 않았어도 보여 주지 않는다 (결과는 세션이 끝나면 사라진다)."""
    if expires_at is not None and expires_at <= datetime.now(timezone.utc):
        raise AppError(410, "SESSION_EXPIRED", "보관 시간이 지나 분석 결과가 삭제됐어요. 새 영상으로 다시 분석해 주세요.")


def own_accident(accident_id: UUID, sid: UUID = Depends(session_id), repo: Repository = Depends(get_repo)) -> dict:
    """URL 의 사고가 이 세션의 것일 때만 돌려준다. 남의 사고는 없는 것처럼 404."""
    accident = repo.get_accident(accident_id, sid)
    if accident is None:
        raise AppError(404, "ACCIDENT_NOT_FOUND", "사고 정보를 찾을 수 없습니다.")
    ensure_not_expired(accident["expires_at"])
    return accident
