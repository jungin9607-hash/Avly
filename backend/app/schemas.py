"""API 요청·응답 형식 (프론트와 합의할 계약).

필드명은 snake_case, 식별자는 UUID, 시간은 UTC ISO 8601 (예: 2026-10-06T01:23:45.123456Z).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import AccidentStatus, AnalysisStatus


class RequestSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class ResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# 공통 오류
class ErrorInfo(ResponseSchema):
    code: str = Field(examples=["ACCIDENT_NOT_FOUND"])
    message: str = Field(examples=["사고 정보를 찾을 수 없습니다."])


class ErrorResponse(ResponseSchema):
    error: ErrorInfo


# 사고
class AccidentCreate(RequestSchema):
    title: str = Field(min_length=1, max_length=200, examples=["퇴근길 차선 변경 사고"])


class AccidentResponse(ResponseSchema):
    id: UUID
    title: str
    status: AccidentStatus
    created_at: datetime


class VideoResponse(ResponseSchema):
    id: UUID
    accident_id: UUID
    video_url: str
    thumbnail: str | None = Field(description="썸네일 URL. 추출 기능 구현 전까지 null")
    duration: float | None = Field(description="영상 길이(초). 추출 기능 구현 전까지 null")
    created_at: datetime


class AccidentDetailResponse(AccidentResponse):
    videos: list[VideoResponse]
    latest_analysis_id: UUID | None = Field(description="가장 최근에 시작한 분석 id. 없으면 null")


# 설문
class SurveyAnswerItem(RequestSchema):
    question: str = Field(min_length=1, max_length=500, examples=["사고 당시 신호는 무엇이었나요?"])
    answer: str = Field(min_length=1, max_length=2000, examples=["초록불이었습니다."])


class SurveyCreate(RequestSchema):
    answers: list[SurveyAnswerItem] = Field(min_length=1, max_length=50)


class SurveyAnswerResponse(ResponseSchema):
    id: UUID
    accident_id: UUID
    question: str
    answer: str
    created_at: datetime


class SurveyResponse(ResponseSchema):
    accident_id: UUID
    answers: list[SurveyAnswerResponse]


# 분석
class AnalysisStartResponse(ResponseSchema):
    analysis_id: UUID
    status: AnalysisStatus
    status_url: str = Field(examples=["/api/v1/analyses/3fa85f64-5717-4562-b3fc-2c963f66afa6"])


class TimelineEventResponse(ResponseSchema):
    id: UUID
    time_sec: float = Field(description="충돌 시점 0초 기준. 충돌 전은 음수")
    event: str
    description: str
    image_url: str | None


class MatchedCaseResponse(ResponseSchema):
    case_id: UUID
    title: str
    summary: str
    fault_ratio: str = Field(examples=["30:70"])
    similarity: float = Field(ge=0, le=1)
    source_url: str | None


class AnalysisResult(ResponseSchema):
    fault_me: int = Field(ge=0, le=100)
    fault_other: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    summary: str
    timeline: list[TimelineEventResponse] = Field(description="time_sec 오름차순")
    matched_cases: list[MatchedCaseResponse] = Field(description="similarity 내림차순")

    @model_validator(mode="after")
    def check_fault_sum(self):
        if self.fault_me + self.fault_other != 100:
            raise ValueError("fault_me 와 fault_other 의 합은 100 이어야 합니다.")
        return self


class AnalysisResponse(ResponseSchema):
    analysis_id: UUID
    accident_id: UUID
    status: AnalysisStatus
    is_mock: bool = Field(description="true 이면 실제 AI가 아닌 개발용 Mock 결과")
    result: AnalysisResult | None = Field(description="status 가 completed 일 때만 값이 있음")
    error: ErrorInfo | None = Field(description="status 가 failed 일 때만 값이 있음")
