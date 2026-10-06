import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.errors import register_error_handlers
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
