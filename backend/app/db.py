"""PostgreSQL 연결과 마이그레이션.

SQLAlchemy Core 로 SQL 을 직접 실행한다. 테이블 정의는 migrations/*.sql 이 유일한 기준이다.
"""

import logging
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from app.config import BASE_DIR, settings

logger = logging.getLogger(__name__)
MIGRATIONS_DIR = BASE_DIR / "migrations"
MIGRATION_LOCK_ID = 727_001  # 여러 프로세스가 동시에 시작해도 마이그레이션을 한 번에 하나만 적용한다


def _driver_url(url: str) -> str:
    """postgresql:// 형식을 psycopg(v3) 드라이버를 쓰는 형식으로 바꾼다."""
    parsed = make_url(url)
    if parsed.drivername in ("postgres", "postgresql"):
        parsed = parsed.set(drivername="postgresql+psycopg")
    return parsed.render_as_string(hide_password=False)


@lru_cache
def get_engine() -> Engine:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL 이 설정되지 않았습니다. backend/.env 또는 docker-compose 의 환경변수를 확인하세요.")
    return create_engine(
        _driver_url(settings.database_url),
        pool_pre_ping=True,   # 풀러가 끊은 연결을 재사용하지 않도록 사용 전에 확인
        pool_size=5,
        max_overflow=5,
        pool_recycle=300,
        connect_args={"connect_timeout": 10},
    )


def check_connection() -> dict[str, str]:
    """읽기 전용 쿼리로 연결을 확인한다. 연결 실패 시 예외를 그대로 올린다."""
    with get_engine().connect() as conn:
        row = conn.execute(text("SELECT current_database(), current_user")).one()
    return {"database": row[0], "user": row[1]}


def migration_files(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    return sorted(directory.glob("*.sql"))


def migrate(engine: Engine | None = None, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """아직 적용하지 않은 migrations/*.sql 을 파일 이름 순서대로 적용하고, 새로 적용한 이름을 돌려준다."""
    engine = engine or get_engine()
    applied_now: list[str] = []
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": MIGRATION_LOCK_ID})
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migration ("
            " name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        ))
        done = {row[0] for row in conn.execute(text("SELECT name FROM schema_migration"))}
        for path in migration_files(directory):
            if path.name in done:
                continue
            logger.info("마이그레이션 적용: %s", path.name)
            conn.exec_driver_sql(path.read_text(encoding="utf-8"))
            conn.execute(text("INSERT INTO schema_migration(name) VALUES (:n)"), {"n": path.name})
            applied_now.append(path.name)
    return applied_now
