import logging

from app import db
from app.config import settings
from app.repository import Repository
from app.worker.ai_compare import make_comparer
from app.worker.cases import make_cases
from app.worker.engines import make_engine
from app.worker.redaction import make_redaction
from app.worker.runner import Worker

logging.basicConfig(level=logging.INFO)


def main() -> None:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    if settings.auto_migrate:
        db.migrate()
    repo = Repository()
    engine = make_engine()
    Worker(repo, engine, make_redaction(), make_cases(repo), make_comparer(repo)).loop()


if __name__ == "__main__":
    main()
