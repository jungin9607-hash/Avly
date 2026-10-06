"""업무 로직. 라우터는 요청/응답 변환만 하고 실제 처리는 여기서 한다."""

import logging
from uuid import UUID

from fastapi import UploadFile

from app import analyzer
from app.errors import AppError
from app.models import (
    Accident,
    AccidentStatus,
    Analysis,
    AnalysisJob,
    AnalysisStatus,
    CaseMatch,
    SurveyAnswer,
    TimelineEvent,
    Video,
)
from app.repository import InMemoryRepository
from app.schemas import (
    AccidentDetailResponse,
    AnalysisResponse,
    AnalysisResult,
    ErrorInfo,
    MatchedCaseResponse,
    SurveyAnswerItem,
    TimelineEventResponse,
    VideoResponse,
)
from app.storage import LocalVideoStorage

logger = logging.getLogger(__name__)

ACTIVE_JOB_STATUSES = {AnalysisStatus.QUEUED, AnalysisStatus.PROCESSING}


def _accident_not_found() -> AppError:
    return AppError(404, "ACCIDENT_NOT_FOUND", "사고 정보를 찾을 수 없습니다.")


def _analysis_not_found() -> AppError:
    return AppError(404, "ANALYSIS_NOT_FOUND", "분석 정보를 찾을 수 없습니다.")


# 사고
def create_accident(repo: InMemoryRepository, title: str) -> Accident:
    return repo.add_accident(Accident(title=title))


def get_accident(repo: InMemoryRepository, accident_id: UUID) -> Accident:
    accident = repo.get_accident(accident_id)
    if accident is None:
        raise _accident_not_found()
    return accident


def get_accident_detail(repo: InMemoryRepository, accident_id: UUID) -> AccidentDetailResponse:
    accident = get_accident(repo, accident_id)
    jobs = repo.list_jobs(accident_id)
    return AccidentDetailResponse(
        id=accident.id,
        title=accident.title,
        status=accident.status,
        created_at=accident.created_at,
        videos=[VideoResponse.model_validate(v) for v in repo.list_videos(accident_id)],
        latest_analysis_id=jobs[-1].id if jobs else None,
    )


# 영상
async def upload_video(
    repo: InMemoryRepository,
    storage: LocalVideoStorage,
    accident_id: UUID,
    upload: UploadFile,
) -> Video:
    get_accident(repo, accident_id)
    stored = await storage.save_video(upload)
    # TODO: 영상 길이(duration)와 썸네일 추출 구현 전까지는 값을 꾸며내지 않고 null 로 둔다.
    return repo.add_video(
        Video(accident_id=accident_id, video_url=stored.url, storage_path=str(stored.path))
    )


# 설문
def save_survey(
    repo: InMemoryRepository, accident_id: UUID, items: list[SurveyAnswerItem]
) -> list[SurveyAnswer]:
    get_accident(repo, accident_id)
    answers = [
        SurveyAnswer(accident_id=accident_id, question=item.question, answer=item.answer)
        for item in items
    ]
    return repo.add_survey_answers(answers)


# 분석
def start_analysis(repo: InMemoryRepository, accident_id: UUID) -> AnalysisJob:
    get_accident(repo, accident_id)

    videos = repo.list_videos(accident_id)
    if not videos:
        raise AppError(409, "VIDEO_REQUIRED", "분석하려면 먼저 사고 영상을 업로드해야 합니다.")

    if any(job.status in ACTIVE_JOB_STATUSES for job in repo.list_jobs(accident_id)):
        raise AppError(409, "ANALYSIS_IN_PROGRESS", "이미 진행 중인 분석이 있습니다.")

    job = repo.add_job(
        AnalysisJob(accident_id=accident_id, video_id=videos[-1].id, is_mock=analyzer.IS_MOCK)
    )
    repo.update_accident_status(accident_id, AccidentStatus.ANALYZING)
    return job


async def run_analysis_job(repo: InMemoryRepository, job_id: UUID) -> None:
    """응답을 보낸 뒤 백그라운드에서 실행된다.

    지금은 같은 서버 프로세스에서 Mock 분석기를 호출한다. 실제 AI 연결 시 작업 큐로 옮길 수 있다.
    """
    job = repo.get_job(job_id)
    repo.update_job_status(job_id, AnalysisStatus.PROCESSING)
    try:
        video = repo.get_video(job.video_id)
        survey = repo.list_survey_answers(job.accident_id)

        output = await analyzer.analyze_accident(video, survey)
        similar_cases = analyzer.search_similar_cases(repo, output)

        analysis = Analysis(
            id=job.id,
            accident_id=job.accident_id,
            fault_me=output.fault_me,
            fault_other=output.fault_other,
            confidence=output.confidence,
            summary=output.summary,
            is_mock=job.is_mock,
        )
        timeline = [
            TimelineEvent(
                analysis_id=job.id,
                time_sec=item.time_sec,
                event=item.event,
                description=item.description,
                image_url=item.image_url,
            )
            for item in output.timeline
        ]
        matches = [
            CaseMatch(analysis_id=job.id, case_id=case_id, similarity=similarity)
            for case_id, similarity in similar_cases
        ]
        repo.save_analysis_result(analysis, timeline, matches)
    except Exception:
        logger.exception("Analysis job %s failed", job_id)
        repo.update_job_status(
            job_id,
            AnalysisStatus.FAILED,
            error_code="ANALYSIS_FAILED",
            error_message="사고 분석 중 오류가 발생했습니다. 다시 시도해 주세요.",
        )
        repo.update_accident_status(job.accident_id, AccidentStatus.FAILED)
        return

    repo.update_job_status(job_id, AnalysisStatus.COMPLETED)
    repo.update_accident_status(job.accident_id, AccidentStatus.COMPLETED)


def get_analysis_view(repo: InMemoryRepository, analysis_id: UUID) -> AnalysisResponse:
    job = repo.get_job(analysis_id)
    if job is None:
        raise _analysis_not_found()

    result = None
    if job.status == AnalysisStatus.COMPLETED:
        result = _build_result(repo, repo.get_analysis(analysis_id))

    error = None
    if job.status == AnalysisStatus.FAILED:
        error = ErrorInfo(code=job.error_code, message=job.error_message)

    return AnalysisResponse(
        analysis_id=job.id,
        accident_id=job.accident_id,
        status=job.status,
        is_mock=job.is_mock,
        result=result,
        error=error,
    )


def _build_result(repo: InMemoryRepository, analysis: Analysis) -> AnalysisResult:
    matched_cases = []
    for match in repo.list_case_matches(analysis.id):
        case = repo.get_legal_case(match.case_id)
        matched_cases.append(
            MatchedCaseResponse(
                case_id=case.id,
                title=case.title,
                summary=case.summary,
                fault_ratio=case.fault_ratio,
                similarity=match.similarity,
                source_url=case.source_url,
            )
        )

    return AnalysisResult(
        fault_me=analysis.fault_me,
        fault_other=analysis.fault_other,
        confidence=analysis.confidence,
        summary=analysis.summary,
        timeline=[TimelineEventResponse.model_validate(e) for e in repo.list_timeline(analysis.id)],
        matched_cases=matched_cases,
    )


# 리포트
def create_report(repo: InMemoryRepository, analysis_id: UUID) -> None:
    job = repo.get_job(analysis_id)
    if job is None:
        raise _analysis_not_found()
    if job.status != AnalysisStatus.COMPLETED:
        raise AppError(409, "ANALYSIS_NOT_COMPLETED", "분석이 완료된 후에 리포트를 생성할 수 있습니다.")

    # TODO(REPORT): PDF 생성 후 Report(analysis_id=..., pdf_url=...)를 저장하고 201 로 반환한다.
    raise AppError(501, "REPORT_NOT_IMPLEMENTED", "PDF 리포트 생성 기능은 아직 구현되지 않았습니다.")
