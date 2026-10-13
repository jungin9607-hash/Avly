import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import db
from app.config import settings
from app.errors import AppError, register_error_handlers
from app.routers import accidents, analyses

logging.basicConfig(level=logging.INFO)

settings.upload_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Avly API",
    version="0.3.0",
    description="Avly v0.3 백엔드. 현재 분석 결과와 판례는 개발용 Mock 데이터입니다.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(accidents.router, prefix="/api/v1")
app.include_router(analyses.router, prefix="/api/v1")

# 개발용 업로드 파일 접근 경로. 운영에서는 객체 스토리지와 접근 제어로 교체한다.
app.mount("/files", StaticFiles(directory=settings.upload_dir), name="files")


@app.get("/", include_in_schema=False)
def root():
    return {"message": "Backend Running"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def health_db():
    """Supabase PostgreSQL 연결 확인. 읽기 전용 쿼리만 실행한다."""
    try:
        return {"status": "ok", **db.check_connection()}
    except Exception as exc:
        # 연결 문자열(비밀번호 포함)이 응답이나 로그에 남지 않도록 예외 종류만 기록한다.
        logging.getLogger(__name__).error("DB 연결 확인 실패: %s", type(exc).__name__)
        raise AppError(503, "DATABASE_UNAVAILABLE", "데이터베이스에 연결할 수 없습니다.") from None
