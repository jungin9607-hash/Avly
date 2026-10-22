"""영상 파일 저장소 (개발용: 로컬 디스크).

운영에서는 객체 저장소(S3 등)로 바꾼다. DB 에는 파일 위치(storage_key)만 저장하고 URL 은 저장하지 않는다.
사용자가 준 파일 이름은 경로로 쓰지 않는다.
"""

from dataclasses import dataclass
from pathlib import Path
import shutil
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.config import settings
from app.errors import AppError

CHUNK_SIZE = 1024 * 1024  # 1MB씩 나눠 읽어 큰 파일도 메모리에 한 번에 올리지 않는다.


@dataclass(frozen=True)
class StoredFile:
    key: str
    path: Path
    size: int


def path_for(key: str) -> Path:
    """storage_key 를 실제 경로로 바꾼다. 업로드 폴더 밖으로 나가는 키는 거부한다."""
    root = settings.upload_dir.resolve()
    path = (root / key).resolve()
    if root != path and root not in path.parents:
        raise ValueError(f"저장소 밖의 경로입니다: {key}")
    return path


def key_for(accident_id: UUID, kind: str, extension: str) -> str:
    # 같은 사고에 동시에 두 번 올라와도 서로 덮어쓰지 않도록 이름에 무작위 값을 붙인다
    return f"{accident_id}/{kind}-{uuid4().hex[:8]}{extension}"


def save_original(accident_id: UUID, upload: UploadFile) -> StoredFile:
    extension = Path(upload.filename or "").suffix.lower()
    if extension not in settings.allowed_video_extensions:
        raise AppError(
            415, "UNSUPPORTED_FILE_TYPE",
            f"허용되지 않는 파일 형식입니다. 허용 확장자: {', '.join(settings.allowed_video_extensions)}",
        )
    key = key_for(accident_id, "original", extension)
    destination = path_for(key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    try:
        with destination.open("wb") as out:
            while chunk := upload.file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > settings.max_upload_size_bytes:
                    raise AppError(
                        413, "FILE_TOO_LARGE",
                        f"파일 용량이 너무 큽니다. 최대 {settings.max_upload_size_mb}MB까지 업로드할 수 있습니다.",
                    )
                out.write(chunk)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    if size == 0:
        destination.unlink(missing_ok=True)
        raise AppError(400, "EMPTY_FILE", "빈 파일은 업로드할 수 없습니다.")
    return StoredFile(key=key, path=destination, size=size)


def delete(key: str) -> bool:
    """파일을 지운다. 이미 없으면 False."""
    path = path_for(key)
    if path.is_file():
        path.unlink()
        return True
    return False


def delete_model_artifacts(video_key: str) -> None:
    """영상과 같은 사고 폴더의 분석 중간 파일을 지운다 (워커 강제 종료 잔여물 포함)."""
    directory = path_for(str(Path(video_key).parent / "_model_results"))
    if directory.exists():
        shutil.rmtree(directory)
