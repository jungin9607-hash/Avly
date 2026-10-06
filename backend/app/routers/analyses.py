from uuid import UUID

from fastapi import APIRouter, Depends

from app import services
from app.repository import InMemoryRepository, get_repository
from app.schemas import AnalysisResponse, ErrorResponse

router = APIRouter(prefix="/analyses", tags=["analyses"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "ANALYSIS_NOT_FOUND"}}


@router.get("/{analysis_id}", response_model=AnalysisResponse, responses=NOT_FOUND)
async def get_analysis(
    analysis_id: UUID,
    repo: InMemoryRepository = Depends(get_repository),
):
    """분석 상태와 결과를 반환한다. completed 가 아니면 result 는 null."""
    return services.get_analysis_view(repo, analysis_id)


@router.post(
    "/{analysis_id}/reports",
    status_code=201,
    responses={
        **NOT_FOUND,
        409: {"model": ErrorResponse, "description": "ANALYSIS_NOT_COMPLETED"},
        501: {"model": ErrorResponse, "description": "REPORT_NOT_IMPLEMENTED"},
    },
)
async def create_report(
    analysis_id: UUID,
    repo: InMemoryRepository = Depends(get_repository),
):
    """PDF 리포트를 생성한다. 현재는 미구현으로 501 을 반환한다."""
    services.create_report(repo, analysis_id)
