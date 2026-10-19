"""라우터가 공통으로 쓰는 의존성."""

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


def own_accident(accident_id: UUID, sid: UUID = Depends(session_id), repo: Repository = Depends(get_repo)) -> dict:
    """URL 의 사고가 이 세션의 것일 때만 돌려준다. 남의 사고는 없는 것처럼 404."""
    accident = repo.get_accident(accident_id, sid)
    if accident is None:
        raise AppError(404, "ACCIDENT_NOT_FOUND", "사고 정보를 찾을 수 없습니다.")
    return accident
