"""환경변수 기반 설정.

backend/.env 파일이 있으면 읽고, 없으면 아래 기본값을 사용한다.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_extension(ext: str) -> str:
    ext = ext.lower()
    return ext if ext.startswith(".") else f".{ext}"


@dataclass(frozen=True)
class Settings:
    cors_origins: list[str]
    public_base_url: str
    upload_dir: Path
    max_upload_size_mb: int
    allowed_video_extensions: list[str]
    mock_analysis_delay_seconds: float

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


def load_settings() -> Settings:
    upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
    if not upload_dir.is_absolute():
        upload_dir = BASE_DIR / upload_dir

    return Settings(
        cors_origins=_split(
            os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        ),
        public_base_url=os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/"),
        upload_dir=upload_dir,
        max_upload_size_mb=int(os.getenv("MAX_UPLOAD_SIZE_MB", "200")),
        allowed_video_extensions=[
            _normalize_extension(ext)
            for ext in _split(os.getenv("ALLOWED_VIDEO_EXTENSIONS", ".mp4,.mov,.avi,.mkv,.webm"))
        ],
        mock_analysis_delay_seconds=float(os.getenv("MOCK_ANALYSIS_DELAY_SECONDS", "3")),
    )


settings = load_settings()
