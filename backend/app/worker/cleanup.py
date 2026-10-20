"""만료 정리. 영상은 파일을 지우고 DB 에는 삭제 시각만 남기며, 세션이 끝난 사고는 분석 결과를 지운다."""

import logging
from datetime import datetime

from app import storage
from app.repository import Repository

logger = logging.getLogger(__name__)


def delete_expired(repo: Repository, at: datetime | None = None) -> int:
    count = 0
    for video in repo.videos_to_delete(at):
        try:
            storage.delete(video["storage_key"])
        except Exception:
            logger.exception("영상 삭제 실패: %s", video["id"])
            continue
        repo.mark_video_deleted(video["id"])
        count += 1
    return count


def scrub_expired(repo: Repository, at: datetime | None = None) -> int:
    """세션이 끝난 사고의 분석 결과를 지운다. 지운 분석 수를 돌려준다."""
    return repo.scrub_expired(at)
