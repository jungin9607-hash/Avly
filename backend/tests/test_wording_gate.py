"""쉬운 말 검수 게이트: 쉬운 말까지 확인한 가감요소만 묻고 계산한다.

- 규칙 숫자를 확인한 유형이어도, 쉬운 말(제목·설명·질문)이 검수 전인 가감요소는 쓰지 않는다.
- 쓰지 않은 가감요소가 있는 유형의 결과는 '모두 확인한 비율(확정)'이 아니라 '확인한 요소만 반영한 비율'이다.
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model"))

from avly.tables import ALL_ADJUSTMENT_RULES, REVIEWED_FACTOR_WORDING, active_rules, wording_gate

FIXTURES = Path(__file__).parent / "fixtures"

try:
    from app import catalog, review_status
    from app.worker import finalize
    from app.worker.engines import ReplayEngine
    HAVE_APP = True
except ImportError:   # 서버 의존성이 없는 PC 에서는 순수 규칙 시험만 한다
    HAVE_APP = False


def rule(factor, actor="A"):
    return {"id": f"{actor}_{factor}", "actor": actor, "factor": factor, "delta_pp": 10, "group": "g"}


class GateTests(unittest.TestCase):
    def test_only_factors_with_reviewed_wording_are_kept_and_the_rest_are_counted(self):
        rules = {"1": {"rules": [rule("a"), rule("b"), rule("c", "B")]}, "2": {"rules": [rule("a"), rule("a", "B")]}}
        kept, held = wording_gate(rules, {"a"})
        self.assertEqual([r["factor"] for r in kept["1"]["rules"]], ["a"])
        self.assertEqual(held, {"1": 2})                       # 1번 유형은 2개를 쓰지 않았다
        self.assertEqual(len(kept["2"]["rules"]), 2)          # 2번 유형은 전부 쓴다
        self.assertNotIn("2", held)

    def test_a_type_with_no_reviewed_wording_becomes_unregistered_but_is_still_counted(self):
        kept, held = wording_gate({"1": {"rules": [rule("x"), rule("y")]}}, {"a"})
        self.assertEqual(kept, {})
        self.assertEqual(held, {"1": 2})

    def test_the_original_config_is_not_changed(self):
        rules = {"1": {"rules": [rule("a"), rule("b")], "reviewed": True}}
        wording_gate(rules, {"a"})
        self.assertEqual(len(rules["1"]["rules"]), 2)

    def test_other_fields_of_a_type_are_kept(self):
        kept, _ = wording_gate({"1": {"rules": [rule("a")], "reviewed": True, "reviewed_by": "김"}}, {"a"})
        self.assertEqual((kept["1"]["reviewed"], kept["1"]["reviewed_by"]), (True, "김"))

    def test_with_the_real_data_every_kept_rule_has_reviewed_wording(self):
        reviewed_types = active_rules(ALL_ADJUSTMENT_RULES, True)
        kept, held = wording_gate(reviewed_types, REVIEWED_FACTOR_WORDING)
        self.assertTrue(all(r["factor"] in REVIEWED_FACTOR_WORDING for c in kept.values() for r in c["rules"]))
        total = sum(len(c["rules"]) for c in reviewed_types.values())
        self.assertEqual(sum(len(c["rules"]) for c in kept.values()) + sum(held.values()), total)   # 쓴 것 + 안 쓴 것 = 전체
        self.assertTrue(set(kept) <= set(reviewed_types))


@unittest.skipUnless(HAVE_APP, "서버 의존성이 없어 건너뜁니다 (worker 컨테이너에서 실행)")
class ResultStateTests(unittest.TestCase):
    def build(self, held_back):
        snapshot, _ = ReplayEngine(directory=FIXTURES).analyze(Path("unused.mp4"), lambda stage: None)
        answers = {q["key"]: "아니요" for q in catalog.adjustment_questions(11, "A")}   # 묻는 항목 전부에 답했다
        with mock.patch.dict(finalize.WORDING_HELD_BACK, {"11": held_back} if held_back else {}, clear=True):
            return finalize.build_result(snapshot, {"accident_type_id": 11, "role": "A", "answers": answers}, [])

    def test_all_answered_and_nothing_held_back_is_final(self):
        result = self.build(0)
        self.assertEqual(result["state"], "final")
        self.assertIsNotNone(result["fault"]["final"])
        self.assertEqual(result["adjustments"]["held_back"], 0)

    def test_all_answered_but_some_factors_held_back_is_only_partial(self):
        result = self.build(2)
        self.assertEqual(result["state"], "partial")
        self.assertIsNone(result["fault"]["final"], "확정 비율로 내보내지 않는다")
        self.assertIsNotNone(result["fault"]["adjusted"], "확인한 요소를 반영한 비율은 보여 준다")
        self.assertEqual(result["adjustments"]["held_back"], 2)
        self.assertIn("확인하지 못한 요소", result["explanation"]["status"])

    def test_base_only_text_says_review_not_registration(self):
        self.assertIn("검수가 끝난", finalize.STATUS_TEXT["base_only"])
        self.assertNotIn("등록되지", finalize.STATUS_TEXT["base_only"])

    def test_held_back_count_comes_from_the_gate(self):
        with mock.patch.dict(catalog.WORDING_HELD_BACK, {"11": 3}, clear=True):
            self.assertEqual((catalog.held_back_count(11), catalog.held_back_count(60)), (3, 0))

    def test_status_tool_counts_types_that_are_really_asked(self):
        rules = {"1": {"rules": [rule("a")], "reviewed": True}, "2": {"rules": [rule("b")], "reviewed": True},
                 "3": {"rules": [rule("a")], "reviewed": False}}
        s = review_status.summarize(rules, {"a": {"reviewed": True}, "b": {"reviewed": False}}, {})
        self.assertEqual(s["rules"]["on_in_service"], [1, 2])
        self.assertEqual(s["rules"]["asked_in_service"], [1])   # 2번은 쉬운 말이 검수 전이라 묻지 않는다
        self.assertIn("가감요소를 실제로 묻는 유형: 1개", review_status.render(s))


if HAVE_APP:
    from tests.test_api import ApiTestCase

    class AdjustmentQuestionsApiTests(ApiTestCase):
        def test_response_tells_how_many_factors_were_not_asked(self):
            _, headers, analysis_id = self.make_awaiting()
            url = f"/api/v1/analyses/{analysis_id}/adjustment-questions?accident_type_id=11&role=A"
            self.assertEqual(self.client.get(url, headers=headers).json()["held_back"], 0)
            with mock.patch.dict(catalog.WORDING_HELD_BACK, {"11": 3}, clear=True):
                body = self.client.get(url, headers=headers).json()
            self.assertEqual(body["held_back"], 3)
            self.assertTrue(body["registered"] and body["questions"])


if __name__ == "__main__":
    unittest.main()
