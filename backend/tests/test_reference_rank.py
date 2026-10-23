import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model"))

from avly.reference_rank import action_fit, order_references, signal_neutral, soft_actions   # noqa: E402

# 표의 진행 문구 → 움직임. 실제 facts.progress_actions 와 같은 모양만 흉내 낸다 (이 시험은 표준 라이브러리만 쓴다)
ACTIONS = {"직진": {"직진"}, "좌회전": {"좌회전"}, "우회전": {"우회전"}, "진로변경": {"진로변경"}, "정지": {"정지/대기"}}


def progress_actions(text):   # 실제 facts.progress_actions 처럼 문구에 들어 있는 동작을 모두 찾는다
    return set().union(*(a for key, a in ACTIONS.items() if key in text))


def row(type_id, feature, place="사거리 교차로(신호등 있음)", code=2):
    return {"accident_type": type_id, "accident_place": code, "accident_place_name": place, "accident_place_feature_name": feature}


def assessment(mismatch=0, score=5.0, assumptions=1, signal_notes=0):
    return {"progress_mismatch_count": mismatch, "score": score, "assumption_count": assumptions,
            "unresolved_conditions": ["A의 '[녹색신호] 직진'에 포함된 신호 조건 확인 필요"] * signal_notes}


def option(role, a_progress, b_progress):
    return {"dashcam_table_role": role, "a_progress": a_progress, "b_progress": b_progress}


class SoftActionTests(unittest.TestCase):
    def test_validated_action_wins_and_unknown_is_filled_from_the_models_record(self):
        checks = [{"vehicle": "A", "action": "좌회전", "support": "관찰"}, {"vehicle": "B", "action": "직진", "support": "추정"}]
        self.assertEqual(soft_actions("직진", "미확인", checks), {"A": "직진", "B": "직진"})   # A 는 검증된 값, B 는 기록으로 채움
        self.assertEqual(soft_actions("미확인", "미확인", checks), {"A": "좌회전", "B": "직진"})

    def test_records_without_support_or_unknown_action_are_ignored(self):
        checks = [{"vehicle": "A", "action": "좌회전", "support": "미확인"}, {"vehicle": "B", "action": "기타", "support": "관찰"}]
        self.assertEqual(soft_actions("미확인", None, checks), {"A": None, "B": None})

    def test_accepts_objects_as_well_as_dicts(self):
        class Check:
            vehicle, action, support = "B", "우회전", "관찰"
        self.assertEqual(soft_actions("미확인", "미확인", [Check()])["B"], "우회전")


class FitTests(unittest.TestCase):
    def test_agreement_and_conflict(self):
        soft = {"A": "좌회전", "B": "직진"}
        self.assertEqual(action_fit(option("A", "좌회전", "직진"), soft, progress_actions), 2)
        self.assertEqual(action_fit(option("A", "직진", "좌회전"), soft, progress_actions), -2)
        self.assertEqual(action_fit(option("A", "좌회전", "좌회전"), soft, progress_actions), 0)
        self.assertEqual(action_fit(option("A", "직진", "직진"), {"A": None, "B": None}, progress_actions), 0)

    def test_tags_and_parentheses_are_conditions_not_actions(self):
        soft = {"A": "좌회전", "B": "직진"}
        # 표: A [녹색 좌회전 신호] 직진 (좌회전 노면표시차로) / B [녹색 좌회전 신호] 좌회전 (직진·좌회전 노면표시차로) — 괄호 속 단어로는 맞다고 보지 않는다
        opposite = option("A", "[녹색 좌회전 신호] 직진 (좌회전 노면표시차로)", "[녹색 좌회전 신호] 좌회전 (직진·좌회전 노면표시차로)")
        self.assertEqual(action_fit(opposite, soft, progress_actions), -2)
        right = option("A", "[녹색 좌회전 신호] 좌회전 (직진 노면표시차로)", "[녹색신호] 직진")
        self.assertEqual(action_fit(right, soft, progress_actions), 2)

    def test_signal_pending_is_not_a_penalty(self):
        self.assertEqual(signal_neutral(assessment(score=4.0, assumptions=2, signal_notes=2)), (5.0, 0))
        self.assertEqual(signal_neutral(assessment(score=4.0, assumptions=2)), (4.0, 2))


class OrderTests(unittest.TestCase):
    soft = {"A": "좌회전", "B": "직진"}

    def order(self, candidates, soft=None, **kw):
        return order_references(candidates, soft or self.soft, progress_actions, **kw)

    def test_role_that_matches_the_observed_actions_comes_first_and_the_wrong_role_is_dropped(self):
        both = [(assessment(), option("A", "직진", "좌회전")), (assessment(), option("B", "좌회전", "직진"))]
        (picked, options), = self.order([(row(1, "f1"), both)])
        self.assertEqual([o["dashcam_table_role"] for o in options], ["B"])   # 내 차 좌회전 / 상대 직진 쪽만

    def test_same_row_keeps_both_roles_when_actions_are_unknown(self):
        both = [(assessment(), option("A", "직진", "좌회전")), (assessment(), option("B", "좌회전", "직진"))]
        (picked, options), = self.order([(row(1, "f1"), both)], soft={"A": None, "B": None})
        self.assertEqual([o["dashcam_table_role"] for o in options], ["A", "B"])

    def test_signal_rows_are_not_always_pushed_behind_non_signal_rows(self):
        plain = (row(10, "노면 표시 위반사고"), [(assessment(score=5.0, assumptions=1), option("A", "좌회전", "직진"))])
        signal = (row(20, "신호 있는 교차로"), [(assessment(score=4.0, assumptions=2, signal_notes=2), option("A", "좌회전", "직진"))])
        order = [r["accident_type"] for r, _ in self.order([plain, signal])]
        self.assertEqual(order, [20, 10])   # 신호 감점을 되돌리면 점수 5.0 대 5.0 → 가정이 더 적은 쪽(신호 유형, 0개)이 앞

    def test_place_the_ai_pointed_to_comes_before_a_better_fitting_row_from_another_place(self):
        unsignaled = (row(10, "대로와 소로", "사거리 교차로(신호등 없음)", 1), [(assessment(score=10.0, assumptions=0), option("A", "좌회전", "직진"))])
        signaled = (row(64, "상대 차량이 측면 방향에서 진입", "사거리 교차로(신호등 있음)", 2), [(assessment(score=9.0, assumptions=2), option("A", "좌회전", "직진"))])
        self.assertEqual([r["accident_type"] for r, _ in self.order([unsignaled, signaled])], [10, 64])   # AI 가 장소를 가리키지 않으면 점수대로
        self.assertEqual([r["accident_type"] for r, _ in self.order([unsignaled, signaled], preferred_places={2})], [64, 10])
        # 가리킨 장소의 행이 없어도 다른 후보가 사라지지는 않는다
        self.assertEqual([r["accident_type"] for r, _ in self.order([unsignaled], preferred_places={2})], [10])

    def test_rows_that_contradict_the_recorded_actions_are_dropped_unless_nothing_else_is_left(self):
        opposite = (row(1, "a"), [(assessment(score=9), option("A", "직진", "좌회전"))])    # 내 차 직진/상대 좌회전: 기록(내 차 좌회전)과 반대
        fits = (row(2, "b"), [(assessment(score=1), option("A", "좌회전", "직진"))])
        self.assertEqual([r["accident_type"] for r, _ in self.order([opposite, fits])], [2])
        self.assertEqual([r["accident_type"] for r, _ in self.order([opposite])], [1])   # 대안이 없으면 그래도 보여 준다

    def test_mismatching_rows_come_last(self):
        bad = (row(1, "a"), [(assessment(mismatch=1, score=9), option("A", "좌회전", "직진"))])
        good = (row(2, "b"), [(assessment(mismatch=0, score=1), option("A", "좌회전", "직진"))])
        self.assertEqual([r["accident_type"] for r, _ in self.order([bad, good])], [2, 1])

    def test_distinct_features_first_then_fill_the_rest(self):
        same = lambda i: (row(i, "같은 특징"), [(assessment(score=9 - i), option("A", "좌회전", "직진"))])
        other = (row(50, "다른 특징"), [(assessment(score=1), option("A", "좌회전", "직진"))])
        order = [r["accident_type"] for r, _ in self.order([same(1), same(2), same(3), other])]
        self.assertEqual(order, [1, 50, 2])   # 같은 특징은 한 번만 먼저, 자리가 남으면 채운다

    def test_total_options_never_exceed_the_limit(self):
        both = lambda i: (row(i, f"f{i}"), [(assessment(), option("A", "좌회전", "직진")), (assessment(), option("B", "좌회전", "직진"))])
        chosen = self.order([both(i) for i in range(1, 6)], soft={"A": None, "B": None})
        self.assertEqual(sum(len(o) for _, o in chosen), 3)
        self.assertEqual([r["accident_type"] for r, _ in chosen], [1, 2])   # 1번 행의 두 역할 + 2번 행의 한 역할

    def test_ties_are_broken_by_type_number_so_the_result_is_stable(self):
        rows = [(row(i, f"f{i}"), [(assessment(), option("A", "좌회전", "직진"))]) for i in (7, 3, 5)]
        self.assertEqual([r["accident_type"] for r, _ in self.order(rows)], [3, 5, 7])


if __name__ == "__main__":
    unittest.main()
