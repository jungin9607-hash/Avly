from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app import catalog
from app import status as st
from app.deps import ensure_not_expired, get_repo
from app.errors import AppError
from app.presenters import analysis_view
from app.repository import NotAwaitingConfirmation, Repository
from app.schemas import AnalysisResponse, ConfirmRequest, ErrorResponse
from app.security import session_id

router = APIRouter(prefix="/analyses", tags=["analyses"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "ANALYSIS_NOT_FOUND"},
             410: {"model": ErrorResponse, "description": "SESSION_EXPIRED (세션이 끝나 결과가 삭제됨)"}}
SESSION = {401: {"model": ErrorResponse, "description": "SESSION_REQUIRED, SESSION_INVALID"}}


def _own_analysis(analysis_id: UUID, sid: UUID, repo: Repository) -> dict:
    row = repo.get_analysis(analysis_id, sid)
    if row is None:
        raise AppError(404, "ANALYSIS_NOT_FOUND", "분석 정보를 찾을 수 없습니다.")
    ensure_not_expired(row["session_expires_at"])
    return row


@router.get("/{analysis_id}", response_model=AnalysisResponse, responses={**NOT_FOUND, **SESSION})
def get_analysis(analysis_id: UUID, sid: UUID = Depends(session_id), repo: Repository = Depends(get_repo)):
    """분석 상태와 결과를 돌려준다. awaiting_confirmation 이면 situation 을, completed 이면 result 를 본다."""
    return analysis_view(_own_analysis(analysis_id, sid, repo))


def _checked_type(accident_type_id: int, role: str) -> None:
    if catalog.get_row(accident_type_id) is None:
        raise AppError(404, "ACCIDENT_TYPE_NOT_FOUND", "과실표에 없는 사고 유형입니다.")


@router.get("/{analysis_id}/adjustment-questions", responses={**NOT_FOUND, **SESSION})
def adjustment_questions(
    analysis_id: UUID,
    accident_type_id: int = Query(description="사용자가 고른 과실표 유형 번호"),
    role: Literal["A", "B"] = Query(description="내 차가 표에서 맡은 쪽"),
    sid: UUID = Depends(session_id),
    repo: Repository = Depends(get_repo),
):
    """고른 유형에 등록된 가감요소를 쉬운 말 질문으로 돌려준다. 등록되지 않은 유형은 빈 목록(기본 비율만 안내)이다.

    쉬운 말 검수가 끝난 가감요소만 묻는다. 검수 전이라 묻지 않은 가감요소 수는 held_back 에 있다."""
    row = _own_analysis(analysis_id, sid, repo)
    _checked_type(accident_type_id, role)
    facts = (row.get("scene") or {}).get("adjustment_facts")
    questions = catalog.adjustment_questions(accident_type_id, role, facts)
    return {"accident_type_id": accident_type_id, "role": role, "registered": bool(questions), "questions": questions,
            "held_back": catalog.held_back_count(accident_type_id)}


@router.post(
    "/{analysis_id}/confirm", response_model=AnalysisResponse, status_code=status.HTTP_202_ACCEPTED,
    responses={**NOT_FOUND, **SESSION, 409: {"model": ErrorResponse, "description": "ANALYSIS_NOT_AWAITING"},
               422: {"model": ErrorResponse, "description": "ROLE_REQUIRED, INVALID_ANSWER, VALIDATION_ERROR"}},
)
def confirm(analysis_id: UUID, body: ConfirmRequest, sid: UUID = Depends(session_id), repo: Repository = Depends(get_repo)):
    """사용자가 확정한 사고 상황과 가감요소 답변을 보낸다. 결과 계산이 시작되고, 완료되면 status 가 completed 가 된다."""
    row = _own_analysis(analysis_id, sid, repo)
    if row["status"] != st.AWAITING_CONFIRMATION:
        raise AppError(409, "ANALYSIS_NOT_AWAITING", "사용자 확인을 기다리는 분석이 아닙니다.")
    answers: dict[str, str] = {}
    if body.accident_type_id is not None:
        if body.role is None:
            raise AppError(422, "ROLE_REQUIRED", "내 차가 표에서 맡은 쪽(role)을 함께 보내야 합니다.")
        _checked_type(body.accident_type_id, body.role)
        valid = {q["key"] for q in catalog.adjustment_questions(body.accident_type_id, body.role)}
        for a in body.answers:
            if a.key not in valid:
                raise AppError(422, "INVALID_ANSWER", f"이 유형에서 묻지 않는 항목입니다: {a.key}")
            if a.key in answers:
                raise AppError(422, "INVALID_ANSWER", f"같은 항목에 답이 두 번 들어 있습니다: {a.key}")
            answers[a.key] = a.answer
    elif body.answers:
        raise AppError(422, "INVALID_ANSWER", "유형을 고르지 않았다면 가감요소에는 답할 수 없습니다.")
    try:
        updated = repo.request_confirm(analysis_id, {"accident_type_id": body.accident_type_id, "role": body.role, "answers": answers})
    except NotAwaitingConfirmation:
        raise AppError(409, "ANALYSIS_NOT_AWAITING", "사용자 확인을 기다리는 분석이 아닙니다.") from None
    return analysis_view(updated)


@router.post(
    "/{analysis_id}/cancel", response_model=AnalysisResponse,
    responses={**NOT_FOUND, **SESSION, 409: {"model": ErrorResponse, "description": "ANALYSIS_NOT_CANCELLABLE"}},
)
def cancel(analysis_id: UUID, sid: UUID = Depends(session_id), repo: Repository = Depends(get_repo)):
    """대기 중이거나 분석 중인 분석을 취소한다. 취소하면 status 가 failed, error.code 가 CANCELLED 가 되어 같은 영상으로 다시 분석할 수 있다.

    분석 중인 작업은 worker 가 지금 하던 단계를 끝낸 뒤에 멈춘다. 이미 취소했으면 같은 응답을 다시 돌려주고,
    이미 끝났거나 사용자 확인 단계라면 409 ANALYSIS_NOT_CANCELLABLE 이다."""
    _own_analysis(analysis_id, sid, repo)
    if repo.cancel_analysis(analysis_id) == "not_cancellable":
        raise AppError(409, "ANALYSIS_NOT_CANCELLABLE", "대기 중이거나 분석 중인 분석만 취소할 수 있습니다.")
    return analysis_view(repo.get_analysis(analysis_id, sid))


@router.post("/{analysis_id}/reports", status_code=501, responses={**NOT_FOUND, **SESSION})
def create_report(analysis_id: UUID, sid: UUID = Depends(session_id), repo: Repository = Depends(get_repo)):
    """서버에서 만드는 PDF 는 아직 없다. 화면의 '분석 결과 저장'은 브라우저의 PDF 저장(인쇄)을 쓴다."""
    row = _own_analysis(analysis_id, sid, repo)
    if row["status"] != st.COMPLETED:
        raise AppError(409, "ANALYSIS_NOT_COMPLETED", "분석이 완료된 후에 리포트를 만들 수 있습니다.")
    raise AppError(501, "REPORT_NOT_IMPLEMENTED", "PDF 리포트 생성 기능은 아직 구현되지 않았습니다.")
