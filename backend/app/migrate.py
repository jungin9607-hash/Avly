"""마이그레이션 확인과 적용. 팀 공용 DB 를 실수로 바꾸지 않도록 기본은 '확인만' 한다.

  python -m app.migrate            어느 DB 에 연결되는지, 아직 적용하지 않은 파일이 무엇인지 보여 준다 (DB 는 바뀌지 않는다)
  python -m app.migrate --apply    대기 중인 파일을 적용한다. 공용 DB 는 한 사람이 팀에 알린 뒤 적용한다.

docker compose 에서:  docker compose exec backend python -m app.migrate
"""
import argparse
import sys

from sqlalchemy.engine import make_url

from app import db
from app.config import settings


def describe(url: str | None) -> str:
    if not url:
        return "(DATABASE_URL 없음)"
    u = make_url(url)
    return f"{u.host}:{u.port or 5432}/{u.database} (사용자 {u.username})"   # 비밀번호는 보여 주지 않는다


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="마이그레이션 확인과 적용")
    parser.add_argument("--apply", action="store_true", help="대기 중인 마이그레이션을 적용한다")
    args = parser.parse_args(argv)

    print("연결 대상:", describe(settings.database_url))
    pending = db.pending_migrations()
    if not pending:
        print("적용할 마이그레이션이 없습니다. (최신 상태)")
        return 0
    print("아직 적용하지 않은 마이그레이션:")
    for name in pending:
        print("  -", name)
    if not args.apply:
        print("\n적용하려면 --apply 를 붙여 다시 실행하세요. 공용 DB 라면 먼저 팀에 알려 주세요.")
        return 0
    print("\n적용합니다...")
    applied = db.migrate()
    print("적용 완료:", ", ".join(applied) if applied else "(없음)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
