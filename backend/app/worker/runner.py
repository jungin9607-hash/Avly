"""worker: DB 의 작업 대기열에서 작업을 하나씩 가져와 처리한다.

- analyze : 번호판·사람 비식별화 → 영상 분석 → 사용자 확인 대기(awaiting_confirmation)
- finalize: 사용자가 확정한 내용으로 결과 계산 → 완료(completed)

분석 코드(avly)는 한 프로세스에서 하나씩만 실행할 수 있어서 worker 한 프로세스는 작업을 하나씩 처리한다.
동시에 여러 분석을 하려면 worker 프로세스를 늘린다.
"""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from app import status as st
from app import storage
from app.config import settings
from app.repository import Repository
from app.worker import cleanup, finalize
from app.worker.engines import EngineNotConfigured

logger = logging.getLogger(__name__)

STALE_JOB_SECONDS = 30 * 60


class NoCases:
    """판례 조회가 없는 기본값 (테스트용)."""

    def related_for(self, accident_type_id: int) -> list[dict]:
        return []


class Worker:
    def __init__(self, repo: Repository, engine, redaction, cases=None):
        self.repo = repo
        self.engine = engine
        self.redaction = redaction
        self.cases = cases or NoCases()
        self._last_maintenance = 0.0

    # ------------------------------------------------------------ 한 건 처리
    def run_once(self) -> bool:
        """대기 중인 작업이 있으면 하나 처리하고 True, 없으면 False."""
        job = self.repo.claim_job()
        if job is None:
            return False
        try:
            if job["kind"] == "analyze":
                self.analyze(job["analysis_id"])
            else:
                self.finalize(job["analysis_id"])
            self.repo.finish_job(job["id"], True)
        except Exception as exc:   # analyze/finalize 가 처리하지 못한 예외: 작업만 실패로 표시한다
            logger.exception("작업 처리 실패: job=%s", job["id"])
            self.repo.finish_job(job["id"], False, f"{type(exc).__name__}: {exc}"[:500])
        return True

    def _fail(self, analysis_id, code: str, message: str) -> None:
        self.repo.update_analysis(analysis_id, status=st.FAILED, stage=None, error_code=code, error_message=message,
                                  finished_at=datetime.now(timezone.utc))

    def analyze(self, analysis_id) -> None:
        from avly import scope   # 예외 종류 (가벼운 모듈)

        analysis = self.repo.get_analysis(analysis_id)
        accident = self.repo.get_accident(analysis["accident_id"])
        self.repo.update_analysis(analysis_id, status=st.PROCESSING, stage="plate_masking", started_at=datetime.now(timezone.utc))
        try:
            masked_path, stats = self._redact(analysis, accident)
            if stats.get("duration"):
                scope.check_duration(stats["duration"])   # AI 를 부르기 전에 길이를 확인한다
            snapshot, logs = self.engine.analyze(masked_path, lambda stage: self.repo.update_analysis(analysis_id, stage=stage))
        except scope.UnsupportedAccident as exc:
            self.repo.update_analysis(analysis_id, status=st.UNSUPPORTED, stage=None, unsupported_reason=str(exc),
                                      finished_at=datetime.now(timezone.utc))
            return
        except scope.VideoTooLong as exc:
            self._fail(analysis_id, "VIDEO_TOO_LONG", str(exc))
            return
        except EngineNotConfigured as exc:
            logger.error("엔진 설정 오류: %s", exc)
            self._fail(analysis_id, "AI_NOT_CONFIGURED", "분석 서비스가 아직 준비되지 않았습니다. 잠시 후 다시 시도해 주세요.")
            return
        except Exception as exc:
            logger.exception("분석 실패: %s", analysis_id)
            if "OPENAI_API_KEY" in str(exc):
                self._fail(analysis_id, "AI_NOT_CONFIGURED", "분석 서비스가 아직 준비되지 않았습니다. 잠시 후 다시 시도해 주세요.")
            else:
                self._fail(analysis_id, "ANALYSIS_FAILED", "사고 분석 중 오류가 발생했습니다. 다시 시도해 주세요.")
            return
        for log in logs:
            self.repo.add_stage_log(analysis_id, **log)
        self.repo.update_analysis(analysis_id, status=st.AWAITING_CONFIRMATION, stage=None, scene=snapshot,
                                  pipeline_version=snapshot.get("model_version"), video_sha256=snapshot.get("video_sha256"),
                                  csv_sha256=snapshot.get("csv_sha256"))

    def _redact(self, analysis, accident) -> tuple[Path, dict]:
        """원본을 가려서 비식별 영상을 만들고 DB 에 올린다. 이후 분석은 이 영상만 쓴다."""
        original = self.repo.get_video_by_id(analysis["video_id"])
        source = storage.path_for(original["storage_key"])
        key = storage.key_for(accident["id"], "masked", ".mp4")
        destination = storage.path_for(key)
        stats = self.redaction.redact(source, destination)
        # 저장 동의가 없으면 비식별 영상도 세션이 끝날 때 지운다. 동의했다면 계속 보관한다.
        expires = None if accident["retention_consent_at"] else accident["expires_at"]
        masked = self.repo.add_video(accident["id"], "masked", key, size_bytes=destination.stat().st_size,
                                     source_video_id=original["id"], expires_at=expires, stats=stats)
        self.repo.update_analysis(analysis["id"], video_id=masked["id"])
        return destination, stats

    def finalize(self, analysis_id) -> None:
        analysis = self.repo.get_analysis(analysis_id)
        confirmed = analysis["confirmed"] or {}
        try:
            type_id = confirmed.get("accident_type_id")
            related = self.cases.related_for(type_id) if type_id is not None else []
            result = finalize.build_result(analysis["scene"], confirmed, related)
        except Exception:
            logger.exception("결과 계산 실패: %s", analysis_id)
            self._fail(analysis_id, "FINALIZE_FAILED", "결과를 계산하는 중 오류가 발생했습니다. 다시 시도해 주세요.")
            return
        final = (result["fault"] or {}).get("final") if result["state"] == "final" else None
        self.repo.update_analysis(
            analysis_id, status=st.COMPLETED, stage=None, result=result, accident_type_id=type_id,
            fault_me=final["me"] if final else None, fault_other=final["other"] if final else None,
            finished_at=datetime.now(timezone.utc))

    # ------------------------------------------------------------ 주기 작업
    def maintenance(self, interval: float = 60.0) -> None:
        """멈춘 작업 재등록과 만료 영상 삭제를 interval 초마다 한 번 한다."""
        if time.monotonic() - self._last_maintenance < interval:
            return
        self._last_maintenance = time.monotonic()
        requeued, failed = self.repo.requeue_stale_jobs(STALE_JOB_SECONDS, settings.avly_max_attempts)
        if requeued or failed:
            logger.warning("멈춘 작업: 다시 등록 %d, 실패 처리 %d", requeued, failed)
        deleted = cleanup.delete_expired(self.repo)
        if deleted:
            logger.info("만료된 영상 %d개를 삭제했습니다.", deleted)

    def loop(self) -> None:
        logger.info("worker 시작: engine=%s, redaction=%s", getattr(self.engine, "name", "?"), getattr(self.redaction, "name", "?"))
        while True:
            self.maintenance()
            if not self.run_once():
                time.sleep(settings.worker_poll_seconds)
