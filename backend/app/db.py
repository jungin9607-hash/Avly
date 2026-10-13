"""PostgreSQL(Supabase) 연결.

DATABASE_URL 이 없으면 엔진을 만들지 않는다(메모리 저장소만 쓰는 개발 모드).
Supabase Session Pooler 로 접속하며 SSL 은 URL 의 sslmode=require 로 켠다.
현재는 연결 확인용이고, 실제 데이터 저장은 아직 repository.py 의 메모리 저장소가 담당한다.
"""

import logging
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from app.config import settings

logger = logging.getLogger(__name__)


def _driver_url(url: str) -> str:
    """postgresql:// 형식을 psycopg(v3) 드라이버를 쓰는 형식으로 바꾼다."""
    parsed = make_url(url)
    if parsed.drivername in ("postgres", "postgresql"):
        parsed = parsed.set(drivername="postgresql+psycopg")
    return parsed.render_as_string(hide_password=False)


@lru_cache
def get_engine() -> Engine | None:
    if not settings.database_url:
        return None

    return create_engine(
        _driver_url(settings.database_url),
        pool_pre_ping=True,  # 풀러가 끊은 연결을 재사용하지 않도록 사용 전에 확인
        pool_size=3,  # 팀원 여럿이 공용 DB를 쓰므로 연결 수를 작게 유지
        max_overflow=2,
        pool_recycle=300,
        connect_args={"connect_timeout": 10},
    )


def check_connection() -> dict[str, str]:
    """읽기 전용 쿼리로 연결을 확인한다. 연결 실패 시 예외를 그대로 올린다."""
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL 이 설정되지 않았습니다.")

    with engine.connect() as conn:
        row = conn.execute(text("SELECT current_database(), current_user")).one()

    return {"database": row[0], "user": row[1]}
