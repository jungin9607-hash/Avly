"""메모리 기반 저장소.

서버를 재시작하면 모든 데이터가 사라진다.
PostgreSQL 연결 시 같은 메서드 이름을 가진 클래스(예: PostgresRepository)를 만들고
get_repository()가 그 인스턴스를 반환하도록 바꾸면 서비스·라우터 코드는 그대로 둘 수 있다.

라우터를 모두 async로 작성해 하나의 이벤트 루프에서만 접근하므로 별도 잠금은 두지 않았다.
"""

from uuid import UUID

from app.models import (
    Accident,
    AccidentStatus,
    Analysis,
    AnalysisJob,
    AnalysisStatus,
    CaseMatch,
    LegalCase,
    SurveyAnswer,
    TimelineEvent,
    Video,
    utcnow,
)


class InMemoryRepository:
    def __init__(self) -> None:
        self.accidents: dict[UUID, Accident] = {}
        self.videos: dict[UUID, Video] = {}
        self.survey_answers: dict[UUID, SurveyAnswer] = {}
        self.analysis_jobs: dict[UUID, AnalysisJob] = {}
        self.analyses: dict[UUID, Analysis] = {}
        self.timeline_events: dict[UUID, TimelineEvent] = {}
        self.legal_cases: dict[UUID, LegalCase] = {}
        self.case_matches: dict[tuple[UUID, UUID], CaseMatch] = {}

    # accident
    def add_accident(self, accident: Accident) -> Accident:
        self.accidents[accident.id] = accident
        return accident

    def get_accident(self, accident_id: UUID) -> Accident | None:
        return self.accidents.get(accident_id)

    def update_accident_status(self, accident_id: UUID, status: AccidentStatus) -> None:
        self.accidents[accident_id].status = status

    # video
    def add_video(self, video: Video) -> Video:
        self.videos[video.id] = video
        return video

    def get_video(self, video_id: UUID) -> Video | None:
        return self.videos.get(video_id)

    def list_videos(self, accident_id: UUID) -> list[Video]:
        videos = [v for v in self.videos.values() if v.accident_id == accident_id]
        return sorted(videos, key=lambda v: v.created_at)

    # survey
    def add_survey_answers(self, answers: list[SurveyAnswer]) -> list[SurveyAnswer]:
        for answer in answers:
            self.survey_answers[answer.id] = answer
        return answers

    def list_survey_answers(self, accident_id: UUID) -> list[SurveyAnswer]:
        answers = [a for a in self.survey_answers.values() if a.accident_id == accident_id]
        return sorted(answers, key=lambda a: a.created_at)

    # analysis job (작업 상태)
    def add_job(self, job: AnalysisJob) -> AnalysisJob:
        self.analysis_jobs[job.id] = job
        return job

    def get_job(self, job_id: UUID) -> AnalysisJob | None:
        return self.analysis_jobs.get(job_id)

    def update_job_status(
        self,
        job_id: UUID,
        status: AnalysisStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        job = self.analysis_jobs[job_id]
        job.status = status
        job.error_code = error_code
        job.error_message = error_message
        job.updated_at = utcnow()

    def list_jobs(self, accident_id: UUID) -> list[AnalysisJob]:
        jobs = [j for j in self.analysis_jobs.values() if j.accident_id == accident_id]
        return sorted(jobs, key=lambda j: j.created_at)

    # analysis result (완료된 결과)
    def save_analysis_result(
        self,
        analysis: Analysis,
        timeline: list[TimelineEvent],
        matches: list[CaseMatch],
    ) -> None:
        # PostgreSQL에서는 이 세 저장을 하나의 트랜잭션으로 묶는다.
        self.analyses[analysis.id] = analysis
        for event in timeline:
            self.timeline_events[event.id] = event
        for match in matches:
            self.case_matches[(match.analysis_id, match.case_id)] = match

    def get_analysis(self, analysis_id: UUID) -> Analysis | None:
        return self.analyses.get(analysis_id)

    def list_timeline(self, analysis_id: UUID) -> list[TimelineEvent]:
        events = [e for e in self.timeline_events.values() if e.analysis_id == analysis_id]
        return sorted(events, key=lambda e: e.time_sec)

    def list_case_matches(self, analysis_id: UUID) -> list[CaseMatch]:
        matches = [m for m in self.case_matches.values() if m.analysis_id == analysis_id]
        return sorted(matches, key=lambda m: m.similarity, reverse=True)

    # legal case
    def add_legal_case(self, case: LegalCase) -> LegalCase:
        self.legal_cases[case.id] = case
        return case

    def get_legal_case(self, case_id: UUID) -> LegalCase | None:
        return self.legal_cases.get(case_id)

    def list_legal_cases(self) -> list[LegalCase]:
        return sorted(self.legal_cases.values(), key=lambda c: c.created_at)


MOCK_LEGAL_CASES = [
    ("차선 변경 중 측면 충돌", "직진 차량 옆으로 차선을 변경하다 충돌한 상황을 가정한 예시입니다.", "30:70"),
    ("교차로 신호 변경 직후 충돌", "황색 신호에 교차로에 진입한 차량과 충돌한 상황을 가정한 예시입니다.", "40:60"),
    ("후방 추돌", "정차 중인 차량을 뒤에서 추돌한 상황을 가정한 예시입니다.", "0:100"),
]


def seed_mock_legal_cases(repo: InMemoryRepository) -> None:
    """테스트용 가상 판례. 실제 판례가 아니다."""
    for title, summary, fault_ratio in MOCK_LEGAL_CASES:
        repo.add_legal_case(
            LegalCase(
                title=f"[테스트용 가상 판례] {title}",
                summary=f"실제 판례가 아닌 개발용 예시입니다. {summary}",
                fault_ratio=fault_ratio,
            )
        )


repository = InMemoryRepository()
seed_mock_legal_cases(repository)


def get_repository() -> InMemoryRepository:
    return repository
