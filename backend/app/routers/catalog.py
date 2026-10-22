import hashlib
import json

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app import catalog

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/accident-types")
def accident_types(request: Request):
    """과실표(차대차 133개 유형)의 전체 선택지. 한 유형이 '내 차가 표의 A일 때'와 'B일 때' 두 개로 나온다.
    프론트는 이 목록으로 장소 → 사고 유형 → 내 차 과정 → 상대 차 과정 순서로 좁혀 간다."""
    items = catalog.options()
    body = {"count": len(items), "items": items}
    # 내용이 바뀌면 바로 새로 받도록, 매번 확인하되 같으면 본문 없이 304 로 답한다 (예전의 1시간 캐시는 문구를 고쳐도 한참 옛 문구가 남았다)
    etag = '"' + hashlib.sha1(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:20] + '"'
    headers = {"ETag": etag, "Cache-Control": "no-cache"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return JSONResponse(body, headers=headers)
