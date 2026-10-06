"""내부 데이터 구조.

데이터 모델 초안(9개 테이블)을 그대로 옮긴 형태다. 지금은 메모리에만 저장하고,
PostgreSQL 연결 시 이 구조를 기준으로 테이블(ORM 모델)을 만든다.
API 응답 형식은 schemas.py에서 따로 정의하므로 여기 있는 내부 필드가 그대로 노출되지는 않는다.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AccidentStatus(StrEnum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(kw_only=True)
class Accident:
    title: str
    status: AccidentStatus = AccidentStatus.UPLOADED
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True)
class Video:
    accident_id: UUID
    video_url: str
    storage_path: str  # 서버 내부 저장 경로. API로 노출하지 않는다.
    thumbnail: str | None = None
    duration: float | None = None  # 초 단위
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True)
class SurveyAnswer:
    accident_id: UUID
    question: str
    answer: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True)
class AnalysisJob:
    """분석 작업 상태. 완료된 결과(Analysis)와 분리해서 관리한다.

    작업 id와 결과 id는 같은 값을 사용하므로 프론트는 analysis_id 하나로 상태와 결과를 조회한다.
    """

    accident_id: UUID
    video_id: UUID
    status: AnalysisStatus = AnalysisStatus.QUEUED
    is_mock: bool = True
    error_code: str | None = None
    error_message: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True)
class Analysis:
    """완료된 분석 결과 (analysis 테이블)."""

    id: UUID
    accident_id: UUID
    fault_me: int
    fault_other: int
    confidence: float
    summary: str
    is_mock: bool
    created_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True)
class TimelineEvent:
    analysis_id: UUID
    time_sec: float  # 충돌 시점 0초, 충돌 전은 음수
    event: str
    description: str
    image_url: str | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass(kw_only=True)
class LegalCase:
    title: str
    summary: str
    fault_ratio: str  # "내 과실:상대 과실" 형식, 예: "30:70"
    source_url: str | None = None
    embedding: list[float] | None = None  # 임베딩 모델 선택 후 차원 확정. API로 노출하지 않는다.
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True)
class CaseMatch:
    """analysis와 legal_case 연결. (analysis_id, case_id)가 복합 PK."""

    analysis_id: UUID
    case_id: UUID
    similarity: float


@dataclass(kw_only=True)
class Report:
    """PDF 리포트 (report 테이블). PDF 생성 구현 시 사용한다."""

    analysis_id: UUID
    pdf_url: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
