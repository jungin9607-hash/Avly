"""판례 조회: DB 에서 먼저 찾고, 부족하면 API 로 가져와 DB 에 저장한다.

흐름 (사고 유형 번호 기준)
1. DB 에 연결된 판례를 읽는다. 목표 개수(3개) 이상이면 끝.
2. 부족하면 유형별 조회 기록(case_lookup)을 본다. 쉬는 시간(retry_after)이 남았으면 API 를 부르지 않는다.
3. 아니면 법령 API 로 가져와 저장한다. 결과가 있으면 7일, 없으면 1일, 오류면 10분 동안 다시 부르지 않는다.
API 오류는 분석을 실패시키지 않는다. DB 에 있는 것만 보여 준다.
"""
import logging
import re
from datetime import datetime, timedelta, timezone

from app import catalog
from app.config import settings
from avly.constants import CASE_TARGET_COUNT

logger = logging.getLogger(__name__)

RETRY_AFTER = {"found": timedelta(days=7), "empty": timedelta(days=1), "error": timedelta(minutes=10)}
SOURCE_LABEL = {"knia_chart": "손해보험협회 도표에 소개된 판례 요약", "law_api": "법령정보 API의 판례", "manual": "직접 입력한 판례"}


def parse_date(value) -> str | None:
    """'2015-12-18', '20151218', '2015.12.18' 같은 값을 YYYY-MM-DD 로 바꾼다. 못 읽으면 None."""
    match = re.search(r"(\d{4})\D{0,3}(\d{1,2})\D{0,3}(\d{1,2})", str(value or ""))
    if not match:
        return None
    try:
        return datetime(int(match[1]), int(match[2]), int(match[3])).date().isoformat()
    except ValueError:
        return None


def _db_case(model_case: dict) -> tuple[dict, dict]:
    """avly 가 만든 판례 dict 를 (legal_case 행, 연결 정보) 로 바꾼다."""
    registered = bool(model_case.get("verified_date"))          # 사람이 검수한 날짜가 적힌 등록 판례
    from_chart = registered or bool(model_case.get("chart_reference"))   # 협회 도표에 실린 참고 판례(검수 전이어도 같은 사고 유형 자료다)
    decided = parse_date(model_case.get("date"))
    verified_at = None
    if registered:
        verified_at = datetime.fromisoformat(parse_date(model_case["verified_date"]) or "2026-01-01").replace(tzinfo=timezone.utc)
    case = {
        "court": model_case["court"], "decided_on": datetime.fromisoformat(decided).date() if decided else None,
        "case_number": model_case["case_number"], "title": model_case.get("case_name"), "summary": model_case["summary"],
        "fault_ratio": None, "source_kind": "knia_chart" if from_chart else "law_api", "source_url": model_case.get("source"),
        # 모델 데이터가 직접 적어 둔 검수 날짜(verified_date)를 그대로 따른다. API 로 가져온 판례는 검수 전이다.
        "verified": registered, "verified_by": "avly 데이터(verified_date)" if registered else None, "verified_at": verified_at,
        "raw": {k: v for k, v in model_case.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))},
        "fetched_at": None if from_chart else datetime.now(timezone.utc),
    }
    link = {"relevance_status": model_case.get("relevance_status") or ("registered_chart_reference" if from_chart else "civil_traffic_context_reference"),
            "comparison_limit": model_case.get("comparison_limit")}
    return case, link


def source_text(row: dict) -> str:
    """AI 비교에 쓰는 판례 본문: 판시사항, 판결요지, 판결 내용 앞부분. API 로 가져온 판례만 있고, 없으면 요약문이다."""
    raw = row.get("raw") or {}
    parts = [raw.get(k) for k in ("holding", "gist", "reasoning") if raw.get(k)]
    return "\n".join(parts) if parts else (row.get("summary") or "")


def view(row: dict) -> dict:
    """DB 행을 화면용 판례로 바꾼다 (비교 내용은 결과를 만들 때 붙인다). `_text` 는 AI 비교용 본문이며 화면과 결과에는 싣지 않는다."""
    return {
        "_text": source_text(row),
        "case_id": str(row["case_id"]), "court": row["court"],
        "date": row["decided_on"].isoformat() if row["decided_on"] else None,
        "case_number": row["case_number"], "title": row["title"], "summary": row["summary"],
        "comparison_limit": row["comparison_limit"], "source_url": row["source_url"], "source_kind": row["source_kind"],
        "source_label": SOURCE_LABEL.get(row["source_kind"], row["source_kind"]), "verified": row["verified"],
        "relevance_status": row["relevance_status"],
    }


class AvlyCaseFetcher:
    """법령 API 로 판례를 찾는다 (avly.law 의 검색을 그대로 쓴다). law_api 키가 없으면 가진 것(등록 자료)만 돌려준다."""

    def fetch(self, accident_type_id: int) -> tuple[list[dict], str]:
        """(판례 목록, 상태). 상태는 'ok' 또는 'unavailable' 등 avly 의 조회 기록 상태."""
        from avly import law
        from avly.context import ctx
        row = catalog.get_row(accident_type_id)
        csv_row = {"accident_type": row.id, "accident_place_name": row.place, "accident_place_feature_name": row.feature,
                   "vehicle_a_progress_info_name": row.a_progress, "vehicle_b_progress_info_name": row.b_progress,
                   "accident_object_name": "차대차"}
        if getattr(ctx, "result_dir", None) is None:   # 판례 검색 응답 캐시를 둘 곳
            ctx.result_dir = settings.upload_dir / "_model_results"
        cases, audit = law.related_cases_for_row(csv_row)
        return cases, audit.get("status", "ok")


class CaseService:
    def __init__(self, repo, fetcher=None, target: int = CASE_TARGET_COUNT):
        self.repo, self.fetcher, self.target = repo, fetcher or AvlyCaseFetcher(), target

    def save(self, accident_type_id: int, model_cases: list[dict]) -> int:
        for model_case in model_cases:
            case, link = _db_case(model_case)
            self.repo.link_case(accident_type_id, self.repo.upsert_case(case), **link)
        return len(model_cases)

    def seed_registered(self) -> int:
        """avly 가 직접 적어 둔 유형별 판례(VERIFIED_CASES)를 DB 에 넣는다. 여러 번 해도 같은 결과다."""
        from avly.tables import VERIFIED_CASES
        return sum(self.save(type_id, cases) for type_id, cases in VERIFIED_CASES.items())

    def related_for(self, accident_type_id: int) -> list[dict]:
        rows = self.repo.cases_for_type(accident_type_id)
        if len(rows) < self.target and self._may_fetch(accident_type_id):
            self._fetch(accident_type_id)
            rows = self.repo.cases_for_type(accident_type_id)
        return [view(r) for r in rows][: max(self.target, 1)]

    def _may_fetch(self, accident_type_id: int) -> bool:
        lookup = self.repo.get_case_lookup(accident_type_id)
        return lookup is None or lookup["retry_after"] is None or lookup["retry_after"] <= datetime.now(timezone.utc)

    def _fetch(self, accident_type_id: int) -> None:
        now = datetime.now(timezone.utc)
        try:
            model_cases, status = self.fetcher.fetch(accident_type_id)
        except Exception:
            logger.exception("판례 조회 실패: 유형 %s", accident_type_id)
            self.repo.set_case_lookup(accident_type_id, "error", 0, now + RETRY_AFTER["error"])
            return
        if status in ("unavailable", "disabled"):   # 키가 없거나 API 에 닿지 못함: 없다고 기록하지 않고 곧 다시 시도한다
            self.save(accident_type_id, model_cases)
            self.repo.set_case_lookup(accident_type_id, "error", len(model_cases), now + RETRY_AFTER["error"])
            return
        count = self.save(accident_type_id, model_cases)
        outcome = "found" if count else "empty"
        self.repo.set_case_lookup(accident_type_id, outcome, count, now + RETRY_AFTER[outcome])


def make_cases(repo, engine=None):
    service = CaseService(repo)
    try:
        service.seed_registered()
    except Exception:
        logger.exception("등록된 판례를 DB 에 넣지 못했습니다.")
    return service
