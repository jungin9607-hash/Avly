"""과실표(차대차 133개 유형)와 가감요소 질문.

과실표 CSV 는 저장소 파일이 기준이고 DB 에 넣지 않는다. 사용자는 "내 차가 표의 A인지 B인지"를 고를 수 있으므로
한 행은 두 가지 방향(role)의 선택지가 된다. role = 내 차가 표에서 맡은 쪽.
"""

import csv
import json
import sys
from dataclasses import dataclass
from functools import lru_cache

from app.config import BASE_DIR, settings

# avly 패키지(backend/model/avly)를 불러올 수 있게 한다
MODEL_DIR = str(BASE_DIR / "model")
if MODEL_DIR not in sys.path:
    sys.path.insert(0, MODEL_DIR)

from avly import explain  # noqa: E402  (표준 라이브러리만 쓰는 모듈이라 서버에서도 가볍게 불러올 수 있다)
from avly.tables import ADJUSTMENT_RULES  # noqa: E402
from avly.constants import PLACE_GROUPS  # noqa: E402,F401

ANSWER_TO_VALUE = {"예": "있음", "아니요": "없음", "잘 모르겠어요": "미확인"}
ANSWER_OPTIONS = list(ANSWER_TO_VALUE)
WHO_KEY = {"내 차": "me", "상대 차": "other"}


def _progress(name: str) -> str:
    """CSV 의 오탈자('출자')를 모델(avly)과 같은 방식으로 고친다. 가감요소 규칙표가 고친 이름을 기준으로 쓰기 때문이다."""
    return name.replace("출자", "출차") if "주차구역" in name else name


@dataclass(frozen=True)
class Row:
    id: int
    place_code: int
    place: str
    feature: str
    a_progress: str
    b_progress: str
    negligence_a: int
    negligence_b: int
    note: str


@lru_cache
def rows() -> dict[int, Row]:
    with settings.fault_table_path.open(encoding="utf-8-sig", newline="") as f:
        table = {}
        for r in csv.DictReader(f):
            row = Row(
                id=int(r["accident_type"]),
                place_code=int(r["accident_place"]),
                place=r["accident_place_name"],
                feature=r["accident_place_feature_name"],
                a_progress=_progress(r["vehicle_a_progress_info_name"]),
                b_progress=_progress(r["vehicle_b_progress_info_name"]),
                negligence_a=int(r["negligence_a"]),
                negligence_b=int(r["negligence_b"]),
                note=r.get("extraction_note", ""),
            )
            if row.negligence_a + row.negligence_b != 100:
                raise ValueError(f"과실표 합계가 100이 아닙니다: 유형 {row.id}")
            table[row.id] = row
    return table


LABELS_PATH = BASE_DIR / "app" / "data" / "accident_labels.json"
LABEL_KINDS = {"place": "places", "feature": "features", "my_progress": "progress", "other_progress": "progress"}


@lru_cache
def labels() -> dict:
    """과실표의 사고 장소·특징·진행 이름을 쉬운 말로 바꾼 표시용 이름. 원래 이름(과실표)은 그대로 둔다."""
    return json.loads(LABELS_PATH.read_text(encoding="utf-8"))


def easy_label(kind: str, original: str) -> str:
    """kind: place | feature | my_progress | other_progress. 쉬운 말이 아직 없으면 원래 이름을 돌려준다."""
    entry = labels().get(LABEL_KINDS[kind], {}).get(original)
    return entry["easy"] if entry and entry.get("easy") else original


def get_row(accident_type_id: int) -> Row | None:
    return rows().get(accident_type_id)


def orient(row: Row, role: str) -> dict:
    """role 이 'A'이면 내 차가 표의 A, 'B'이면 내 차가 표의 B."""
    mine_is_a = role == "A"
    my_progress = row.a_progress if mine_is_a else row.b_progress
    other_progress = row.b_progress if mine_is_a else row.a_progress
    return {
        "accident_type_id": row.id,
        "role": role,
        "place": row.place,
        "feature": row.feature,
        "my_progress": my_progress,
        "other_progress": other_progress,
        # 화면에는 쉬운 말을 크게 보여 주고, 위의 원래 이름(과실표 표기)은 작게 함께 보여 준다
        "easy": {
            "place": easy_label("place", row.place),
            "feature": easy_label("feature", row.feature),
            "my_progress": easy_label("my_progress", my_progress),
            "other_progress": easy_label("other_progress", other_progress),
        },
        "base_me": row.negligence_a if mine_is_a else row.negligence_b,
        "base_other": row.negligence_b if mine_is_a else row.negligence_a,
    }


def options() -> list[dict]:
    """프론트가 장소 → 사고 유형 → 내 차 과정 → 상대 차 과정 순서로 좁혀 가는 데 쓰는 전체 선택지.

    화면에 보이는 네 항목이 같으면 하나로 줄인다 (번호가 가장 작은 유형을 남긴다).
    - 양쪽 진행이 같고 50:50 인 유형은 내 차가 A 든 B 든 같으므로 하나만 둔다
    - 과실표에 같은 상황이 두 번 적힌 경우(예: 114번과 116번)도 하나만 둔다
    """
    seen: dict[tuple, dict] = {}
    for row in sorted(rows().values(), key=lambda r: r.id):
        for role in ("A", "B"):
            option = orient(row, role)
            key = (option["place"], option["feature"], option["my_progress"], option["other_progress"])
            seen.setdefault(key, option)
    return list(seen.values())


def adjustment_questions(accident_type_id: int, role: str, facts: list[dict] | None = None) -> list[dict]:
    """선택한 유형에 등록된 가감요소 질문. 등록되지 않은 유형은 빈 목록이다(기본 비율만 안내).

    facts: 분석 단계에서 영상으로 관찰·추정한 가감요소 [{actor('A'=내 차, 'B'=상대 차), factor, value, status, reason}].
    있으면 질문마다 AI 제안(suggested)을 붙인다. 사용자의 최종 답이 우선한다.
    """
    config = ADJUSTMENT_RULES.get(str(accident_type_id))
    if config is None:
        return []
    by_key = {(f["actor"], f["factor"]): f for f in (facts or []) if f.get("status") in ("observed", "inferred")}
    questions = []
    for rule in config["rules"]:
        who = "내 차" if rule["actor"] == role else "상대 차"
        dashcam_actor = "A" if who == "내 차" else "B"
        e = explain.explain_factor(rule["factor"], rule["delta_pp"], who)
        suggestion = None
        fact = by_key.get((dashcam_actor, rule["factor"]))
        if fact and fact.get("value") in ("있음", "없음"):
            suggestion = {
                "answer": "예" if fact["value"] == "있음" else "아니요",
                "basis": "영상에서 관찰" if fact["status"] == "observed" else "영상에서 추정",
                "evidence": fact.get("reason") or None,
            }
        questions.append({
            "key": f"{WHO_KEY[who]}.{rule['factor']}",
            "factor": rule["factor"],
            "who": who,
            "group": rule.get("group"),
            "title": e["title"],
            "easy": e["easy"],
            "question": e["question"],
            "effect": e["effect"],
            "delta_pp": rule["delta_pp"],
            "needs_user": bool(rule.get("manual_only")),
            "requires_other_adjustment": bool(rule.get("requires_B_adjustment")),
            "options": ANSWER_OPTIONS,
            "suggested": suggestion,
            "reviewed": e["reviewed"],
        })
    return questions


def answers_to_facts(answers: dict[str, str]) -> list[dict]:
    """사용자의 답({'other.signal_delay': '예'})을 규칙 엔진이 읽는 사실 목록으로 바꾼다. 사용자 답은 status='user'."""
    facts = []
    for key, answer in answers.items():
        who, _, factor = key.partition(".")
        if who not in ("me", "other") or not factor or answer not in ANSWER_TO_VALUE:
            raise ValueError(f"알 수 없는 답변입니다: {key}={answer}")
        facts.append({
            "actor": "A" if who == "me" else "B",
            "factor": factor,
            "value": ANSWER_TO_VALUE[answer],
            "status": "user",
            "evidence_frame_ids": [],
            "source": "사용자 확인; 영상 검증과 별도",
            "reason": "가감 요소 확인 질문에 대한 사용자 답변",
        })
    return facts
