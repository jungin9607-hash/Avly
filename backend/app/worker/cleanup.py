"""만료된 영상 삭제. 파일을 지우고 DB 에는 삭제 시각만 남긴다 (처리 이력은 남긴다)."""

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
