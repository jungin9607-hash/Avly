from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status

from app import services
from app.repository import InMemoryRepository, get_repository
from app.schemas import (
    AccidentCreate,
    AccidentDetailResponse,
    AccidentResponse,
    AnalysisStartResponse,
    ErrorResponse,
    SurveyAnswerResponse,
    SurveyCreate,
    SurveyResponse,
    VideoResponse,
)
from app.storage import LocalVideoStorage, get_video_storage

router = APIRouter(prefix="/accidents", tags=["accidents"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "ACCIDENT_NOT_FOUND"}}


@router.post("", response_model=AccidentResponse, status_code=status.HTTP_201_CREATED)
async def create_accident(
    body: AccidentCreate,
    repo: InMemoryRepository = Depends(get_repository),
):
    """사고를 생성한다. 초기 상태는 uploaded."""
    return AccidentResponse.model_validate(services.create_accident(repo, body.title))


@router.get("/{accident_id}", response_model=AccidentDetailResponse, responses=NOT_FOUND)
async def get_accident(
    accident_id: UUID,
    repo: InMemoryRepository = Depends(get_repository),
):
    """사고 기본 정보, 현재 상태, 업로드된 영상 목록, 최근 분석 id를 반환한다."""
    return services.get_accident_detail(repo, accident_id)


@router.post(
    "/{accident_id}/videos",
    response_model=VideoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        **NOT_FOUND,
        400: {"model": ErrorResponse, "description": "EMPTY_FILE"},
        413: {"model": ErrorResponse, "description": "FILE_TOO_LARGE"},
        415: {"model": ErrorResponse, "description": "UNSUPPORTED_FILE_TYPE"},
    },
)
async def upload_video(
    accident_id: UUID,
    file: UploadFile = File(description="사고 영상 파일"),
    repo: InMemoryRepository = Depends(get_repository),
    storage: LocalVideoStorage = Depends(get_video_storage),
):
    """multipart/form-data 의 file 필드로 영상을 업로드한다."""
    video = await services.upload_video(repo, storage, accident_id, file)
    return VideoResponse.model_validate(video)


@router.post(
    "/{accident_id}/survey",
    response_model=SurveyResponse,
    status_code=status.HTTP_201_CREATED,
    responses=NOT_FOUND,
)
async def save_survey(
    accident_id: UUID,
    body: SurveyCreate,
    repo: InMemoryRepository = Depends(get_repository),
):
    """설문 응답을 저장하고, 이번 요청에서 저장된 응답 목록을 반환한다."""
    answers = services.save_survey(repo, accident_id, body.answers)
    return SurveyResponse(
        accident_id=accident_id,
        answers=[SurveyAnswerResponse.model_validate(a) for a in answers],
    )


@router.post(
    "/{accident_id}/analyses",
    response_model=AnalysisStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        **NOT_FOUND,
        409: {"model": ErrorResponse, "description": "VIDEO_REQUIRED 또는 ANALYSIS_IN_PROGRESS"},
    },
)
async def start_analysis(
    accident_id: UUID,
    background_tasks: BackgroundTasks,
    repo: InMemoryRepository = Depends(get_repository),
):
    """분석 작업을 만들고 바로 202 를 반환한다. 결과는 status_url 을 polling 해서 확인한다."""
    job = services.start_analysis(repo, accident_id)
    background_tasks.add_task(services.run_analysis_job, repo, job.id)
    return AnalysisStartResponse(
        analysis_id=job.id,
        status=job.status,
        status_url=f"/api/v1/analyses/{job.id}",
    )
