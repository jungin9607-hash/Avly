"""환경변수 기반 설정.

backend/.env 파일이 있으면 읽고, 없으면 아래 기본값을 사용한다. 값은 코드 어디서나 settings 로 읽는다.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _extension(ext: str) -> str:
    ext = ext.lower()
    return ext if ext.startswith(".") else f".{ext}"


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    cors_origins: list[str]
    upload_dir: Path
    max_upload_size_mb: int
    allowed_video_extensions: list[str]
    app_secret: str                 # 영상 서명 URL 에 쓰는 비밀값. 운영에서는 반드시 바꾼다.
    session_ttl_hours: int          # 이 시간이 지나면 원본 영상을 삭제한다 (accident.expires_at)
    unsupported_retention_hours: int  # 차대차가 아니라 분석하지 않은 영상을 보관하는 시간 (저장 동의와 무관)
    media_url_ttl_seconds: int      # 영상 서명 URL 유효 시간
    auto_migrate: bool              # 시작할 때 migrations/*.sql 을 적용한다
    engine: str                     # fake | replay | avly  (worker 가 쓰는 분석 엔진)
    redaction: str                  # yolo | dev_copy  (dev_copy 는 개발용: 가리지 않고 복사만 한다)
    worker_poll_seconds: float
    fault_table_path: Path
    replay_dir: Path
    avly_max_attempts: int
    case_compare: str               # auto | ai | rule  (판례 비교 방식. auto 는 실제 엔진과 OpenAI 키가 있으면 ai)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


def load_settings() -> Settings:
    upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
    if not upload_dir.is_absolute():
        upload_dir = BASE_DIR / upload_dir
    return Settings(
        database_url=os.getenv("DATABASE_URL") or None,
        cors_origins=_split(os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")),
        upload_dir=upload_dir,
        max_upload_size_mb=int(os.getenv("MAX_UPLOAD_SIZE_MB", "200")),
        allowed_video_extensions=[_extension(e) for e in _split(os.getenv("ALLOWED_VIDEO_EXTENSIONS", ".mp4,.mov,.avi"))],
        app_secret=os.getenv("APP_SECRET", "dev-only-secret-change-me"),
        session_ttl_hours=int(os.getenv("SESSION_TTL_HOURS", "24")),
        unsupported_retention_hours=int(os.getenv("UNSUPPORTED_RETENTION_HOURS", "24")),
        media_url_ttl_seconds=int(os.getenv("MEDIA_URL_TTL_SECONDS", "600")),
        auto_migrate=os.getenv("AUTO_MIGRATE", "false").lower() in ("1", "true", "yes"),   # 공용 DB 를 실수로 바꾸지 않도록 기본은 끈다
        engine=os.getenv("ENGINE", "avly").lower(),
        redaction=os.getenv("REDACTION", "yolo").lower(),
        worker_poll_seconds=float(os.getenv("WORKER_POLL_SECONDS", "2")),
        fault_table_path=Path(os.getenv("FAULT_TABLE_PATH", str(BASE_DIR / "model" / "avly" / "data" / "fault_table_car_to_car.csv"))),
        replay_dir=Path(os.getenv("REPLAY_DIR", str(BASE_DIR / "tests" / "fixtures"))),
        avly_max_attempts=int(os.getenv("JOB_MAX_ATTEMPTS", "2")),
        case_compare=os.getenv("CASE_COMPARE", "auto").lower(),
    )


settings = load_settings()
