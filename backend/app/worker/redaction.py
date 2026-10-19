"""비식별화 단계. 분석과 저장에는 이 단계가 만든 영상만 쓴다.

- yolo      : 번호판은 검은 박스, 사람은 전체 블러 (backend/plate/redact.py). 운영에서 쓴다.
- dev_copy  : 개발용. 가리지 않고 복사만 한다. 운영에서는 쓰면 안 된다 (개인정보가 그대로 남는다).
"""

import logging
import shutil
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class YoloRedaction:
    name = "yolo"

    def __init__(self):
        self._redactor = None

    def redact(self, source: Path, destination: Path) -> dict:
        from plate import redact   # 무거운 의존성(ultralytics 등)은 실제로 쓸 때만 불러온다
        if self._redactor is None:
            self._redactor = redact.default_redactor()   # 모델은 처음 한 번만 불러온다
        return redact.redact_video(source, destination, redactor=self._redactor)


class DevCopyRedaction:
    name = "dev_copy"

    def redact(self, source: Path, destination: Path) -> dict:
        logger.warning("REDACTION=dev_copy: 영상을 가리지 않고 복사합니다. 개발용입니다.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        return {}


def make_redaction(name: str | None = None):
    name = (name or settings.redaction).lower()
    if name == "yolo":
        return YoloRedaction()
    if name == "dev_copy":
        return DevCopyRedaction()
    raise ValueError(f"알 수 없는 REDACTION 입니다: {name} (yolo, dev_copy 중 하나)")
