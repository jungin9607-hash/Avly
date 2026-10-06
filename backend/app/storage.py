"""개발용 로컬 영상 저장소.

업로드한 파일을 UPLOAD_DIR/videos/ 에 저장하고 main.py의 /files 경로로 누구나 접근할 수 있게 한다.
운영에서는 S3 같은 객체 스토리지와 접근 제어(서명 URL 등)로 교체해야 한다.
"""

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import settings
from app.errors import AppError

CHUNK_SIZE = 1024 * 1024  # 1MB씩 나눠 읽어 큰 파일도 메모리에 한 번에 올리지 않는다.


@dataclass(frozen=True)
class StoredFile:
    path: Path
    url: str


class LocalVideoStorage:
    def __init__(
        self,
        root: Path,
        public_base_url: str,
        max_bytes: int,
        allowed_extensions: list[str],
    ) -> None:
        self.video_dir = root / "videos"
        self.public_base_url = public_base_url
        self.max_bytes = max_bytes
        self.allowed_extensions = allowed_extensions

    async def save_video(self, upload: UploadFile) -> StoredFile:
        extension = Path(upload.filename or "").suffix.lower()
        if extension not in self.allowed_extensions:
            raise AppError(
                415,
                "UNSUPPORTED_FILE_TYPE",
                f"허용되지 않는 파일 형식입니다. 허용 확장자: {', '.join(self.allowed_extensions)}",
            )

        # 사용자 파일명은 경로로 쓰지 않고, 서버가 만든 UUID 이름으로 저장한다.
        filename = f"{uuid4()}{extension}"
        self.video_dir.mkdir(parents=True, exist_ok=True)
        destination = self.video_dir / filename

        size = 0
        try:
            with destination.open("wb") as out:
                while chunk := await upload.read(CHUNK_SIZE):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise AppError(
                            413,
                            "FILE_TOO_LARGE",
                            f"파일 용량이 너무 큽니다. 최대 {self.max_bytes // (1024 * 1024)}MB까지 업로드할 수 있습니다.",
                        )
                    out.write(chunk)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise

        if size == 0:
            destination.unlink(missing_ok=True)
            raise AppError(400, "EMPTY_FILE", "빈 파일은 업로드할 수 없습니다.")

        return StoredFile(path=destination, url=f"{self.public_base_url}/files/videos/{filename}")


video_storage = LocalVideoStorage(
    root=settings.upload_dir,
    public_base_url=settings.public_base_url,
    max_bytes=settings.max_upload_size_bytes,
    allowed_extensions=settings.allowed_video_extensions,
)


def get_video_storage() -> LocalVideoStorage:
    return video_storage
