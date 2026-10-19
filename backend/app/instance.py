"""이 PC(설치)의 이름표. 팀이 같은 DB 를 쓸 때 작업과 영상이 누구 것인지 구분한다.

영상 파일은 각자의 PC(upload 폴더)에만 있다. 그래서 작업 대기열에는 소유자를 적고, worker 는 자기 작업만 가져가며,
만료 영상 삭제도 자기 영상만 한다. 이름표는 upload 폴더의 `.instance_id` 에 처음 한 번 만들어 api 와 worker 가 같이 쓴다.
"""
import os
import uuid

from app.config import settings

_cached: str | None = None


def instance_id() -> str:
    global _cached
    if _cached:
        return _cached
    path = settings.upload_dir / ".instance_id"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:   # api 와 worker 가 동시에 처음 시작해도 하나만 만들어지게 한다
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w") as f:
            f.write(uuid.uuid4().hex[:12])
    except FileExistsError:
        pass
    _cached = path.read_text().strip()
    return _cached
