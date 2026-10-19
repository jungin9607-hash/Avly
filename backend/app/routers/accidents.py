from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from app import storage
from app.config import settings
from app.deps import get_repo, own_accident
from app.errors import AppError
from app.repository import ActiveAnalysisExists, Repository
from app.schemas import (
    AccidentCreate,
    AccidentCreated,
    AccidentDetailResponse,
    AnalysisStartResponse,
    ErrorResponse,
    VideoResponse,
    VideoUrlResponse,
)
from app.security import sign_media

router = APIRouter(prefix="/accidents", tags=["accidents"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "ACCIDENT_NOT_FOUND"}}
SESSION = {401: {"model": ErrorResponse, "description": "SESSION_REQUIRED, SESSION_INVALID"}}


@router.post(
    "", response_model=AccidentCreated, status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ErrorResponse, "description": "CONSENT_REQUIRED 또는 VALIDATION_ERROR"}},
)
def create_accident(body: AccidentCreate, repo: Repository = Depends(get_repo)):
    """사고를 만든다. 분석 동의(consent.analysis)가 true 여야 한다. 응답의 session_id 를 이후 요청의 X-Session-Id 로 보낸다."""
    if not body.consent.analysis:
        raise AppError(422, "CONSENT_REQUIRED", "분석 동의가 필요합니다.")
    return repo.create_accident(body.title, body.consent.version, body.consent.retention, settings.session_ttl_hours)


@router.get("/{accident_id}", response_model=AccidentDetailResponse, responses={**NOT_FOUND, **SESSION})
def get_accident(accident: dict = Depends(own_accident), repo: Repository = Depends(get_repo)):
    original = repo.get_video(accident["id"], "original")
    return {**accident, "video": original, "latest_analysis_id": repo.latest_analysis_id(accident["id"])}


@router.post(
    "/{accident_id}/videos", response_model=VideoResponse, status_code=status.HTTP_201_CREATED,
    responses={
        **NOT_FOUND, **SESSION,
        400: {"model": ErrorResponse, "description": "EMPTY_FILE"},
        409: {"model": ErrorResponse, "description": "VIDEO_ALREADY_UPLOADED"},
        413: {"model": ErrorResponse, "description": "FILE_TOO_LARGE"},
        415: {"model": ErrorResponse, "description": "UNSUPPORTED_FILE_TYPE"},
    },
)
def upload_video(
    file: UploadFile = File(description="사고 영상 파일 (사고마다 하나)"),
    accident: dict = Depends(own_accident),
    repo: Repository = Depends(get_repo),
):
    """multipart/form-data 의 file 필드로 영상을 올린다. 영상은 사고마다 하나만 올릴 수 있다."""
    if repo.has_original(accident["id"]):
        raise AppError(409, "VIDEO_ALREADY_UPLOADED", "영상은 사고마다 하나만 올릴 수 있습니다.")
    stored = storage.save_original(accident["id"], file)
    try:
        return repo.add_video(accident["id"], "original", stored.key, size_bytes=stored.size, expires_at=accident["expires_at"])
    except Exception as exc:
        storage.delete(stored.key)
        if "uq_video_original" in str(exc):  # 동시에 두 번 올라온 경우
            raise AppError(409, "VIDEO_ALREADY_UPLOADED", "영상은 사고마다 하나만 올릴 수 있습니다.") from None
        raise


@router.get("/{accident_id}/video-url", response_model=VideoUrlResponse, responses={**NOT_FOUND, **SESSION})
def video_url(accident: dict = Depends(own_accident), repo: Repository = Depends(get_repo)):
    """번호판·사람을 가린 영상을 재생할 수 있는 짧게 유효한 주소. 원본은 어떤 경우에도 제공하지 않는다."""
    masked = repo.get_video(accident["id"], "masked")
    if masked is None or not storage.path_for(masked["storage_key"]).is_file():
        return {"available": False, "url": None, "expires_at": None}
    token, expires = sign_media(accident["id"], "masked")
    return {"available": True, "url": f"/api/v1/media/{token}", "expires_at": datetime.fromtimestamp(expires, timezone.utc)}


@router.post(
    "/{accident_id}/analyses", response_model=AnalysisStartResponse, status_code=status.HTTP_202_ACCEPTED,
    responses={**NOT_FOUND, **SESSION, 409: {"model": ErrorResponse, "description": "VIDEO_REQUIRED 또는 ANALYSIS_IN_PROGRESS"}},
)
def start_analysis(accident: dict = Depends(own_accident), repo: Repository = Depends(get_repo)):
    """분석을 시작하고 바로 202 를 돌려준다. 결과는 status_url 을 반복해서 조회해 확인한다."""
    original = repo.get_video(accident["id"], "original")
    if original is None:
        raise AppError(409, "VIDEO_REQUIRED", "분석하려면 먼저 사고 영상을 올려야 합니다.")
    try:
        analysis = repo.create_analysis(accident["id"], original["id"])
    except ActiveAnalysisExists:
        raise AppError(409, "ANALYSIS_IN_PROGRESS", "이미 진행 중인 분석이 있습니다.") from None
    return {"analysis_id": analysis["id"], "status": analysis["status"], "status_url": f"/api/v1/analyses/{analysis['id']}"}
