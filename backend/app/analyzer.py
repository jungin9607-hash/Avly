"""분석 엔진 연결 지점.

지금은 고정된 Mock 결과를 돌려준다. 실제 AI와 판례 검색(RAG)을 연결할 때는
이 파일의 두 함수 내부만 교체하면 되도록 입력과 출력 형태를 고정해 두었다.
"""

import asyncio
from dataclasses import dataclass
from uuid import UUID

from app.config import settings
from app.models import SurveyAnswer, Video
from app.repository import InMemoryRepository

IS_MOCK = True


@dataclass(frozen=True)
class TimelineItem:
    time_sec: float
    event: str
    description: str
    image_url: str | None = None


@dataclass(frozen=True)
class AnalyzerOutput:
    fault_me: int
    fault_other: int
    confidence: float
    summary: str
    timeline: list[TimelineItem]


async def analyze_accident(video: Video, survey: list[SurveyAnswer]) -> AnalyzerOutput:
    # TODO(AI): 실제 영상 분석 모델 호출로 교체한다.
    #   - video.storage_path 의 영상과 survey 응답을 입력으로 사용
    #   - 오래 걸리는 작업이면 별도 작업 큐(Celery, RQ 등)나 외부 AI 서버로 분리
    #   - 실패 시 예외를 던지면 services.run_analysis_job 이 작업을 failed 로 기록한다
    await asyncio.sleep(settings.mock_analysis_delay_seconds)
    return AnalyzerOutput(
        fault_me=30,
        fault_other=70,
        confidence=0.85,
        summary="개발용 Mock 분석 결과입니다. 실제 영상을 분석한 결과가 아닙니다.",
        timeline=[
            TimelineItem(-3.0, "차선 변경 시작", "테스트용 사건 설명입니다. 상대 차량이 차선 변경을 시작합니다."),
            TimelineItem(-1.5, "거리 좁혀짐", "테스트용 사건 설명입니다. 두 차량의 간격이 급격히 줄어듭니다."),
            TimelineItem(0.0, "충돌", "테스트용 사건 설명입니다. 두 차량이 측면으로 충돌합니다."),
            TimelineItem(2.0, "정차", "테스트용 사건 설명입니다. 두 차량이 갓길에 정차합니다."),
        ],
    )


def search_similar_cases(
    repo: InMemoryRepository, output: AnalyzerOutput, top_k: int = 3
) -> list[tuple[UUID, float]]:
    # TODO(RAG): output.summary 를 임베딩하고 pgvector 로 legal_case.embedding 과
    #   코사인 유사도가 높은 판례 top_k 개를 찾는다. 지금은 테스트용 가상 판례를 고정 순서로 반환한다.
    mock_similarities = [0.91, 0.84, 0.77]
    cases = repo.list_legal_cases()[:top_k]
    return [(case.id, similarity) for case, similarity in zip(cases, mock_similarities)]
