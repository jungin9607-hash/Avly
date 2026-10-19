"""DB 행을 API 응답 형태로 바꾼다."""

from app import status as st


def analysis_view(row: dict) -> dict:
    scene = row.get("scene") or {}
    error = None
    if row["status"] == st.FAILED:
        error = {"code": row.get("error_code") or "ANALYSIS_FAILED",
                 "message": row.get("error_message") or "사고 분석 중 오류가 발생했습니다. 다시 시도해 주세요."}
    return {
        "analysis_id": row["id"],
        "accident_id": row["accident_id"],
        "status": row["status"],
        "stage": st.stage_info(row["stage"]) if row["status"] == st.PROCESSING else None,
        "situation": scene.get("situation"),
        "result": row.get("result") if row["status"] == st.COMPLETED else None,
        "unsupported_reason": row.get("unsupported_reason") if row["status"] == st.UNSUPPORTED else None,
        "error": error,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
