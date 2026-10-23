"""분석 상태와 진행 단계 정의."""

QUEUED = "queued"
PROCESSING = "processing"
AWAITING_CONFIRMATION = "awaiting_confirmation"
COMPLETED = "completed"
FAILED = "failed"
UNSUPPORTED = "unsupported"

ACTIVE = (QUEUED, PROCESSING, AWAITING_CONFIRMATION)

# (단계 id, 사용자에게 보여줄 이름). 순서가 index 이다.
STAGES = [
    ("plate_masking", "번호판·사람 비식별화"),
    ("overview", "전체 흐름 분석"),
    ("detail_review", "사고 전후 상세 확인"),
    ("case_matching", "과실 유형 비교"),
    ("finalize", "결과 정리"),
]
STAGE_INDEX = {sid: i + 1 for i, (sid, _) in enumerate(STAGES)}
STAGE_LABEL = dict(STAGES)


def stage_info(stage: str | None) -> dict | None:
    if stage is None:
        return None
    return {"id": stage, "index": STAGE_INDEX[stage], "total": len(STAGES), "label": STAGE_LABEL[stage]}
