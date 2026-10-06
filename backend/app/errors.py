"""오류 응답 형식 통일.

모든 오류는 {"error": {"code": ..., "message": ...}} 형태로 반환한다.
요청 검증 오류(422)만 어떤 필드가 잘못됐는지 알려주는 details를 추가로 포함한다.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """업무 오류. 서비스 코드에서 raise하면 통일된 형식으로 응답한다."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(status_code: int, code: str, message: str, details=None) -> JSONResponse:
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error})


_HTTP_ERROR_CODES = {
    404: ("NOT_FOUND", "요청한 경로를 찾을 수 없습니다."),
    405: ("METHOD_NOT_ALLOWED", "허용되지 않는 HTTP 메서드입니다."),
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        details = [
            {
                "field": ".".join(str(part) for part in err["loc"]),
                "message": err["msg"],
                "type": err["type"],
            }
            for err in exc.errors()
        ]
        return error_response(422, "VALIDATION_ERROR", "요청 형식이 올바르지 않습니다.", details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        code, message = _HTTP_ERROR_CODES.get(exc.status_code, ("HTTP_ERROR", str(exc.detail)))
        return error_response(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.exception("Unhandled error")
        return error_response(500, "INTERNAL_SERVER_ERROR", "서버 내부 오류가 발생했습니다.")
