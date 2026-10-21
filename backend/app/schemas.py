"""API 요청·응답 형식 (프론트와 합의한 계약).

필드명은 snake_case, 식별자는 UUID, 시간은 UTC ISO 8601.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RequestSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class ResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorInfo(ResponseSchema):
    code: str = Field(examples=["ACCIDENT_NOT_FOUND"])
    message: str


class ErrorResponse(ResponseSchema):
    error: ErrorInfo


# ---------------------------------------------------------------- 사고
class Consent(RequestSchema):
    version: str = Field(min_length=1, max_length=20, description="사용자가 본 동의 문서의 버전")
    analysis: bool = Field(description="분석 동의 (필수). true 여야 한다")
    retention: bool = Field(default=False, description="영상 저장·추가 활용 동의 (선택)")


class AccidentCreate(RequestSchema):
    title: str = Field(min_length=1, max_length=200, examples=["퇴근길 차선 변경 사고"])
    consent: Consent


class AccidentResponse(ResponseSchema):
    id: UUID
    title: str
    status: str
    created_at: datetime
    expires_at: datetime | None


class AccidentCreated(AccidentResponse):
    session_id: UUID = Field(description="이후 모든 요청의 X-Session-Id 헤더에 넣는다")


class VideoResponse(ResponseSchema):
    id: UUID
    accident_id: UUID
    size_bytes: int | None
    created_at: datetime


class AccidentDetailResponse(AccidentResponse):
    video: VideoResponse | None
    latest_analysis_id: UUID | None


class VideoUrlResponse(ResponseSchema):
    available: bool = Field(description="비식별 영상을 재생할 수 있는지. 보관하지 않았거나 삭제됐으면 false")
    url: str | None
    expires_at: datetime | None


# ---------------------------------------------------------------- 분석
class StageInfo(ResponseSchema):
    id: str
    index: int
    total: int
    label: str


class AnalysisStartResponse(ResponseSchema):
    analysis_id: UUID
    status: str
    status_url: str


class AnalysisResponse(ResponseSchema):
    analysis_id: UUID
    accident_id: UUID
    status: Literal["queued", "processing", "awaiting_confirmation", "completed", "failed", "unsupported"]
    stage: StageInfo | None
    situation: dict[str, Any] | None = Field(description="status 가 awaiting_confirmation 이후일 때: AI 가 파악한 사고 상황과 후보")
    result: dict[str, Any] | None = Field(description="status 가 completed 일 때만 값이 있음")
    unsupported_reason: str | None
    error: ErrorInfo | None
    created_at: datetime
    updated_at: datetime


class AnswerIn(RequestSchema):
    key: str = Field(min_length=3, max_length=80, examples=["other.signal_delay"])
    answer: Literal["예", "아니요", "잘 모르겠어요"]


class StartAnalysisRequest(RequestSchema):
    place: str | None = Field(default=None, description="사고 장소 종류(선택). 고르면 그 장소의 유형만 비교한다. 예: 주차장, 사거리 교차로")


class ConfirmRequest(RequestSchema):
    accident_type_id: int | None = Field(
        description="사용자가 확정한 과실표 유형 번호. 표에 맞는 유형이 없으면 null (결과는 '확정 불가'로 나온다)")
    role: Literal["A", "B"] | None = Field(default=None, description="내 차가 표에서 맡은 쪽. accident_type_id 가 있으면 필수")
    answers: list[AnswerIn] = Field(default_factory=list, max_length=60)
