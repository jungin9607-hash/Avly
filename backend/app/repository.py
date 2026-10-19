"""DB 접근. SQL 을 직접 실행하고 결과는 dict 로 돌려준다.

여러 단계가 함께 성공하거나 실패해야 하는 작업(분석 만들기 + 작업 등록 등)은 한 트랜잭션으로 묶는다.
"""

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError

from app import status as st
from app.db import get_engine


class ActiveAnalysisExists(Exception):
    """사고에 이미 진행 중인 분석이 있다."""


class NotAwaitingConfirmation(Exception):
    """사용자 확인을 기다리는 상태가 아니다."""


def _rows(result) -> list[dict]:
    return [dict(r._mapping) for r in result]


def _one(result) -> dict | None:
    row = result.first()
    return dict(row._mapping) if row else None


def _q(sql: str, *jsonb: str):
    """JSONB 로 보낼 파라미터 이름을 지정해 쿼리를 만든다."""
    stmt = text(sql)
    if jsonb:
        stmt = stmt.bindparams(*[bindparam(name, type_=JSONB) for name in jsonb])
    return stmt


def now() -> datetime:
    return datetime.now(timezone.utc)


class Repository:
    def __init__(self, engine=None):
        self.engine = engine or get_engine()

    # ------------------------------------------------------------ accident
    def create_accident(self, title: str, consent_version: str, retention: bool, ttl_hours: int) -> dict:
        created = now()
        row = {
            "id": uuid4(), "title": title, "session_id": uuid4(), "version": consent_version,
            "consent_at": created, "retention_at": created if retention else None,
            "expires_at": created + timedelta(hours=ttl_hours),
        }
        with self.engine.begin() as conn:
            return _one(conn.execute(text(
                "INSERT INTO accident (id, title, session_id, consent_version, consent_at, retention_consent_at, expires_at)"
                " VALUES (:id, :title, :session_id, :version, :consent_at, :retention_at, :expires_at) RETURNING *"), row))

    def get_accident(self, accident_id: UUID, session_id: UUID | None = None) -> dict | None:
        """session_id 를 주면 그 세션의 사고일 때만 돌려준다 (다른 사람의 사고는 없는 것처럼 취급)."""
        sql = "SELECT * FROM accident WHERE id = :id" + (" AND session_id = :sid" if session_id else "")
        with self.engine.connect() as conn:
            return _one(conn.execute(text(sql), {"id": accident_id, "sid": session_id}))

    def set_accident_status(self, accident_id: UUID, status: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE accident SET status = :s WHERE id = :id"), {"s": status, "id": accident_id})

    # ------------------------------------------------------------ video
    def add_video(self, accident_id: UUID, kind: str, storage_key: str, size_bytes: int | None = None,
                  source_video_id: UUID | None = None, sha256: str | None = None, expires_at: datetime | None = None,
                  stats: dict | None = None) -> dict:
        stats = stats or {}
        row = {
            "id": uuid4(), "accident_id": accident_id, "kind": kind, "source": source_video_id, "key": storage_key,
            "sha": sha256, "size": size_bytes, "expires": expires_at,
            "duration": stats.get("duration"), "fps": stats.get("fps"), "width": stats.get("width"), "height": stats.get("height"),
            "total": stats.get("frames"), "pf": stats.get("frames_with_plates"), "pd": stats.get("plate_detections"),
            "qf": stats.get("frames_with_people"), "qd": stats.get("person_detections"),
        }
        with self.engine.begin() as conn:
            return _one(conn.execute(text(
                "INSERT INTO video (id, accident_id, kind, source_video_id, storage_key, sha256, size_bytes, expires_at,"
                " duration, fps, width, height, redact_frames_total, plate_frames_detected, plate_detections,"
                " person_frames_detected, person_detections)"
                " VALUES (:id, :accident_id, :kind, :source, :key, :sha, :size, :expires, :duration, :fps, :width, :height,"
                " :total, :pf, :pd, :qf, :qd) RETURNING *"), row))

    def get_video(self, accident_id: UUID, kind: str) -> dict | None:
        """가장 최근의, 파일이 지워지지 않은 영상."""
        with self.engine.connect() as conn:
            return _one(conn.execute(text(
                "SELECT * FROM video WHERE accident_id = :a AND kind = :k AND deleted_at IS NULL"
                " ORDER BY created_at DESC LIMIT 1"), {"a": accident_id, "k": kind}))

    def get_video_by_id(self, video_id: UUID) -> dict | None:
        with self.engine.connect() as conn:
            return _one(conn.execute(text("SELECT * FROM video WHERE id = :id"), {"id": video_id}))

    def has_original(self, accident_id: UUID) -> bool:
        with self.engine.connect() as conn:
            return conn.execute(text("SELECT 1 FROM video WHERE accident_id = :a AND kind = 'original'"), {"a": accident_id}).first() is not None

    def update_video(self, video_id: UUID, **fields) -> None:
        allowed = {"duration", "fps", "width", "height", "sha256"}
        assert set(fields) <= allowed, set(fields) - allowed
        if not fields:
            return
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        with self.engine.begin() as conn:
            conn.execute(text(f"UPDATE video SET {sets} WHERE id = :id"), {**fields, "id": video_id})

    def mark_video_deleted(self, video_id: UUID) -> None:
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE video SET deleted_at = now() WHERE id = :id"), {"id": video_id})

    def expire_accident_videos(self, accident_id: UUID, hours: int) -> None:
        """사고에 딸린 영상의 삭제 시각을 지금부터 hours 시간 뒤로 당긴다 (저장 동의와 상관없이)."""
        with self.engine.begin() as conn:
            conn.execute(text(
                "UPDATE video SET expires_at = now() + make_interval(hours => :h) WHERE accident_id = :a AND deleted_at IS NULL"),
                {"h": hours, "a": accident_id})

    def videos_to_delete(self, at: datetime | None = None) -> list[dict]:
        """만료 시각이 지났는데 아직 파일이 남아 있는 영상."""
        with self.engine.connect() as conn:
            return _rows(conn.execute(text(
                "SELECT * FROM video WHERE expires_at IS NOT NULL AND expires_at <= :t AND deleted_at IS NULL"),
                {"t": at or now()}))

    # ------------------------------------------------------------ analysis
    def create_analysis(self, accident_id: UUID, video_id: UUID) -> dict:
        """분석을 만들고 'analyze' 작업을 등록한다. 진행 중인 분석이 있으면 ActiveAnalysisExists."""
        analysis_id = uuid4()
        try:
            with self.engine.begin() as conn:
                row = _one(conn.execute(text(
                    "INSERT INTO analysis (id, accident_id, video_id, status, attempt)"
                    " VALUES (:id, :a, :v, 'queued', (SELECT COALESCE(MAX(attempt), 0) + 1 FROM analysis WHERE accident_id = :a))"
                    " RETURNING *"), {"id": analysis_id, "a": accident_id, "v": video_id}))
                conn.execute(text("INSERT INTO job (analysis_id, kind) VALUES (:id, 'analyze')"), {"id": analysis_id})
                conn.execute(text("UPDATE accident SET status = 'analyzing' WHERE id = :a"), {"a": accident_id})
                return row
        except IntegrityError as exc:
            if "uq_analysis_active" in str(exc):
                raise ActiveAnalysisExists from None
            raise

    def get_analysis(self, analysis_id: UUID, session_id: UUID | None = None) -> dict | None:
        sql = ("SELECT a.* FROM analysis a JOIN accident ac ON ac.id = a.accident_id WHERE a.id = :id"
               + (" AND ac.session_id = :sid" if session_id else ""))
        with self.engine.connect() as conn:
            return _one(conn.execute(text(sql), {"id": analysis_id, "sid": session_id}))

    def latest_analysis_id(self, accident_id: UUID) -> UUID | None:
        with self.engine.connect() as conn:
            row = conn.execute(text("SELECT id FROM analysis WHERE accident_id = :a ORDER BY created_at DESC LIMIT 1"), {"a": accident_id}).first()
            return row[0] if row else None

    def update_analysis(self, analysis_id: UUID, **fields) -> None:
        """분석 행을 고친다. scene, confirmed, result 는 JSON 으로 저장한다."""
        allowed = {"status", "stage", "video_id", "error_code", "error_message", "unsupported_reason", "accident_type_id",
                   "fault_me", "fault_other", "scene", "confirmed", "result", "pipeline_version", "video_sha256",
                   "csv_sha256", "started_at", "finished_at"}
        assert set(fields) <= allowed, set(fields) - allowed
        json_fields = tuple(f for f in ("scene", "confirmed", "result") if f in fields)
        sets = ", ".join(f"{k} = :{k}" for k in fields) + ", updated_at = now()"
        with self.engine.begin() as conn:
            conn.execute(_q(f"UPDATE analysis SET {sets} WHERE id = :id", *json_fields), {**fields, "id": analysis_id})
            if "status" in fields:  # 사고의 상태도 함께 맞춘다
                mapping = {st.COMPLETED: "completed", st.FAILED: "failed", st.UNSUPPORTED: "unsupported"}
                accident_status = mapping.get(fields["status"], "analyzing")
                conn.execute(text("UPDATE accident SET status = :s WHERE id = (SELECT accident_id FROM analysis WHERE id = :id)"),
                             {"s": accident_status, "id": analysis_id})

    def request_confirm(self, analysis_id: UUID, confirmed: dict) -> dict:
        """사용자 확인 내용을 저장하고 'finalize' 작업을 등록한다. 확인 대기 상태가 아니면 NotAwaitingConfirmation."""
        with self.engine.begin() as conn:
            row = _one(conn.execute(_q(
                "UPDATE analysis SET status = 'processing', stage = 'finalize', confirmed = :confirmed, updated_at = now()"
                " WHERE id = :id AND status = 'awaiting_confirmation' RETURNING *", "confirmed"),
                {"confirmed": confirmed, "id": analysis_id}))
            if row is None:
                raise NotAwaitingConfirmation
            conn.execute(text("INSERT INTO job (analysis_id, kind) VALUES (:id, 'finalize')"), {"id": analysis_id})
            return row

    # ------------------------------------------------------------ job (worker)
    def claim_job(self) -> dict | None:
        """대기 중인 작업 하나를 가져온다. 다른 worker 가 가져간 것은 건너뛴다."""
        with self.engine.begin() as conn:
            return _one(conn.execute(text(
                "UPDATE job SET status = 'running', locked_at = now(), attempts = attempts + 1"
                " WHERE id = (SELECT id FROM job WHERE status = 'queued' ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1)"
                " RETURNING *")))

    def finish_job(self, job_id: int, ok: bool, error: str | None = None) -> None:
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE job SET status = :s, finished_at = now(), error = :e WHERE id = :id"),
                         {"s": "done" if ok else "failed", "e": error, "id": job_id})

    def requeue_stale_jobs(self, max_age_seconds: int, max_attempts: int) -> tuple[int, int]:
        """worker 가 죽어서 오래 running 인 작업을 다시 대기열로 돌린다. 시도 횟수를 넘긴 것은 실패로 처리한다."""
        with self.engine.begin() as conn:
            requeued = conn.execute(text(
                "UPDATE job SET status = 'queued', locked_at = NULL"
                " WHERE status = 'running' AND locked_at < now() - make_interval(secs => :age) AND attempts < :max"),
                {"age": max_age_seconds, "max": max_attempts}).rowcount
            failed = conn.execute(text(
                "UPDATE job SET status = 'failed', finished_at = now(), error = 'worker 가 응답하지 않아 중단됨'"
                " WHERE status = 'running' AND locked_at < now() - make_interval(secs => :age) AND attempts >= :max"),
                {"age": max_age_seconds, "max": max_attempts}).rowcount
            return requeued, failed

    def add_stage_log(self, analysis_id: UUID, stage: str, provider: str | None = None, model: str | None = None,
                      input_tokens: int | None = None, output_tokens: int | None = None, cached: bool = False,
                      latency_ms: int | None = None, status: str = "ok") -> None:
        with self.engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO analysis_stage_log (analysis_id, stage, provider, model, input_tokens, output_tokens, cached, latency_ms, status)"
                " VALUES (:a, :stage, :p, :m, :i, :o, :c, :l, :s)"),
                {"a": analysis_id, "stage": stage, "p": provider, "m": model, "i": input_tokens, "o": output_tokens,
                 "c": cached, "l": latency_ms, "s": status})

    # ------------------------------------------------------------ 판례 (DB 먼저, 없으면 API 로 보충)
    def upsert_case(self, case: dict) -> UUID:
        """판례를 저장한다. (법원, 사건번호)가 같으면 갱신하되, 이미 검수된 표시는 낮추지 않는다."""
        row = {"id": uuid4(), **{k: case.get(k) for k in (
            "court", "decided_on", "case_number", "title", "summary", "fault_ratio", "source_kind", "source_url",
            "verified", "verified_by", "verified_at", "raw", "fetched_at")}}
        row["verified"] = bool(row["verified"])
        with self.engine.begin() as conn:
            return conn.execute(_q(
                "INSERT INTO legal_case (id, court, decided_on, case_number, title, summary, fault_ratio, source_kind, source_url,"
                " verified, verified_by, verified_at, raw, fetched_at)"
                " VALUES (:id, :court, :decided_on, :case_number, :title, :summary, :fault_ratio, :source_kind, :source_url,"
                " :verified, :verified_by, :verified_at, :raw, :fetched_at)"
                " ON CONFLICT (court, case_number) DO UPDATE SET"
                " title = COALESCE(EXCLUDED.title, legal_case.title), summary = EXCLUDED.summary,"
                " source_url = COALESCE(EXCLUDED.source_url, legal_case.source_url),"
                " raw = COALESCE(EXCLUDED.raw, legal_case.raw), fetched_at = COALESCE(EXCLUDED.fetched_at, legal_case.fetched_at),"
                " verified = legal_case.verified OR EXCLUDED.verified,"
                " verified_by = CASE WHEN legal_case.verified THEN legal_case.verified_by ELSE EXCLUDED.verified_by END,"
                " verified_at = CASE WHEN legal_case.verified THEN legal_case.verified_at ELSE EXCLUDED.verified_at END"
                " RETURNING id", "raw"), row).scalar_one()

    def link_case(self, accident_type_id: int, case_id: UUID, relevance_status: str, comparison_limit: str | None) -> None:
        with self.engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO case_accident_type (accident_type_id, case_id, relevance_status, comparison_limit)"
                " VALUES (:t, :c, :r, :l) ON CONFLICT (accident_type_id, case_id) DO UPDATE SET"
                " relevance_status = EXCLUDED.relevance_status, comparison_limit = EXCLUDED.comparison_limit"),
                {"t": accident_type_id, "c": case_id, "r": relevance_status, "l": comparison_limit})

    def cases_for_type(self, accident_type_id: int) -> list[dict]:
        """이 유형에 연결된 판례. 도표 등록, 조건이 모두 맞는 판례, 일부만 맞는 판례 순서이고 같은 단계에서는 검수된 것, 최근 것이 먼저."""
        with self.engine.connect() as conn:
            return _rows(conn.execute(text(
                "SELECT c.id AS case_id, c.court, c.decided_on, c.case_number, c.title, c.summary, c.fault_ratio, c.source_kind,"
                " c.source_url, c.verified, c.verified_at, l.relevance_status, l.comparison_limit"
                " FROM case_accident_type l JOIN legal_case c ON c.id = l.case_id WHERE l.accident_type_id = :t"
                " ORDER BY (l.relevance_status = 'partial_reference'), c.verified DESC, c.decided_on DESC NULLS LAST, c.case_number"), {"t": accident_type_id}))

    def get_case_lookup(self, accident_type_id: int) -> dict | None:
        with self.engine.connect() as conn:
            return _one(conn.execute(text("SELECT * FROM case_lookup WHERE accident_type_id = :t"), {"t": accident_type_id}))

    def set_case_lookup(self, accident_type_id: int, status: str, case_count: int, retry_after: datetime | None) -> None:
        with self.engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO case_lookup (accident_type_id, status, case_count, looked_up_at, retry_after)"
                " VALUES (:t, :s, :n, now(), :r) ON CONFLICT (accident_type_id) DO UPDATE SET"
                " status = EXCLUDED.status, case_count = EXCLUDED.case_count, looked_up_at = now(), retry_after = EXCLUDED.retry_after"),
                {"t": accident_type_id, "s": status, "n": case_count, "r": retry_after})
