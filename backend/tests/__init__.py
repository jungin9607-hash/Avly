"""테스트 환경 설정. 어떤 app 모듈보다 먼저 환경변수를 정해야 하므로 여기서 한다."""

import logging
import os
import tempfile

if os.environ.get("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp(prefix="avly-uploads-"))
os.environ["AUTO_MIGRATE"] = "false"
os.environ["APP_SECRET"] = "test-secret"
os.environ["SESSION_TTL_HOURS"] = "24"
os.environ.setdefault("AVLY_REQUIRE_RULE_REVIEW", "0")   # 시험에서는 검수 전 규칙도 전부 켠다. 켜고 끄는 동작은 test_rule_review.py 가 따로 확인한다

# 테스트 출력에 요청 로그가 쏟아지지 않게 한다
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("app.db").setLevel(logging.WARNING)
