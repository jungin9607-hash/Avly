import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import settings
from app.errors import AppError, register_error_handlers
from app.routers import accidents, analyses, catalog, media

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    if settings.auto_migrate:
        applied = db.migrate()
        if applied:
            logger.info("적용한 마이그레이션: %s", ", ".join(applied))
    yield


app = FastAPI(
    title="Avly API",
    version="0.4.0",
    description="Avly v0.4 백엔드. 분석은 worker 가 처리하고, 이 서버는 요청 접수와 상태·결과 조회만 한다.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

for router in (accidents.router, analyses.router, catalog.router, media.router):
    app.include_router(router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def root():
    return {"message": "Backend Running"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def health_db():
    """PostgreSQL 연결 확인. 읽기 전용 쿼리만 실행한다."""
    try:
        return {"status": "ok", **db.check_connection()}
    except Exception as exc:
        # 연결 문자열(비밀번호 포함)이 응답이나 로그에 남지 않도록 예외 종류만 기록한다.
        logger.error("DB 연결 확인 실패: %s", type(exc).__name__)
        raise AppError(503, "DATABASE_UNAVAILABLE", "데이터베이스에 연결할 수 없습니다.") from None
