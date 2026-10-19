from fastapi import APIRouter, Response

from app import catalog

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/accident-types")
def accident_types(response: Response):
    """과실표(차대차 133개 유형)의 전체 선택지. 한 유형이 '내 차가 표의 A일 때'와 'B일 때' 두 개로 나온다.
    프론트는 이 목록으로 장소 → 사고 유형 → 내 차 과정 → 상대 차 과정 순서로 좁혀 간다."""
    response.headers["Cache-Control"] = "public, max-age=3600"
    items = catalog.options()
    return {"count": len(items), "items": items}
