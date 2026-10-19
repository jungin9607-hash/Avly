import mimetypes

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app import storage
from app.deps import get_repo
from app.errors import AppError
from app.security import verify_media

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{token}")
def media(token: str):
    """서명된 주소로 비식별 영상을 재생한다 (Range 요청 지원). 주소는 짧게 유효하다."""
    accident_id, kind = verify_media(token)
    if kind != "masked":  # 원본은 서명이 있어도 제공하지 않는다
        raise AppError(403, "MEDIA_LINK_INVALID", "영상 주소가 올바르지 않거나 만료되었습니다.")
    video = get_repo().get_video(accident_id, "masked")
    if video is None:
        raise AppError(404, "VIDEO_NOT_AVAILABLE", "재생할 수 있는 영상이 없습니다.")
    path = storage.path_for(video["storage_key"])
    if not path.is_file():
        raise AppError(404, "VIDEO_NOT_AVAILABLE", "재생할 수 있는 영상이 없습니다.")
    media_type = mimetypes.guess_type(path.name)[0] or "video/mp4"
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "private, no-store"})
