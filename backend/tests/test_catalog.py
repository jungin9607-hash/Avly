import unittest

from app import catalog


class CatalogTests(unittest.TestCase):
    def test_loads_133_car_to_car_types(self):
        rows = catalog.rows()
        self.assertEqual(len(rows), 133)
        self.assertEqual(sorted(rows)[0], 0)
        self.assertEqual(sorted(rows)[-1], 132)

    def test_every_type_has_two_orientations_and_sums_to_100(self):
        options = catalog.options()
        self.assertEqual(len(options), 266)
        for o in options:
            self.assertEqual(o["base_me"] + o["base_other"], 100)

    def test_orientation_swaps_progress_and_fault(self):
        row = catalog.get_row(11)
        a, b = catalog.orient(row, "A"), catalog.orient(row, "B")
        self.assertEqual((a["my_progress"], a["other_progress"]), ("후행 직진", "선행 진로변경"))
        self.assertEqual((a["base_me"], a["base_other"]), (30, 70))
        self.assertEqual((b["my_progress"], b["other_progress"]), ("선행 진로변경", "후행 직진"))
        self.assertEqual((b["base_me"], b["base_other"]), (70, 30))

    def test_unregistered_type_has_no_questions(self):
        self.assertEqual(catalog.adjustment_questions(0, "A"), [])

    def test_registered_type_questions_follow_roles(self):
        # 유형 11: 표의 B(선행 진로변경)에 방향지시등 가감요소가 있다
        as_a = {q["key"]: q for q in catalog.adjustment_questions(11, "A")}   # 내 차 = 표의 A(후행 직진)
        as_b = {q["key"]: q for q in catalog.adjustment_questions(11, "B")}   # 내 차 = 표의 B(선행 진로변경)
        self.assertEqual(as_a["other.signal_delay"]["who"], "상대 차")
        self.assertEqual(as_b["me.signal_delay"]["who"], "내 차")
        self.assertNotIn("me.signal_delay", as_a)
        q = as_a["other.signal_delay"]
        self.assertEqual(q["options"], ["예", "아니요", "잘 모르겠어요"])
        self.assertEqual(q["effect"], "상대 차 과실 +10%p")
        self.assertTrue(q["question"].startswith("상대 차가"))
        self.assertFalse(q["needs_user"])
        self.assertTrue(as_a["me.gross_negligence"]["needs_user"])

    def test_keys_are_unique_per_type(self):
        for type_id in (1, 3, 11, 21, 27, 126, 128):
            for role in ("A", "B"):
                keys = [q["key"] for q in catalog.adjustment_questions(type_id, role)]
                self.assertEqual(len(keys), len(set(keys)), (type_id, role))

    def test_suggestions_use_only_observed_or_inferred_facts(self):
        facts = [
            {"actor": "B", "factor": "signal_delay", "value": "있음", "status": "observed", "reason": "방향지시등 미점등 장면"},
            {"actor": "B", "factor": "prohibited_change", "value": "있음", "status": "user"},
            {"actor": "B", "factor": "bus_lane_violation", "value": "미확인", "status": "unknown"},
        ]
        qs = {q["key"]: q for q in catalog.adjustment_questions(11, "A", facts)}
        self.assertEqual(qs["other.signal_delay"]["suggested"], {"answer": "예", "basis": "영상에서 관찰", "evidence": "방향지시등 미점등 장면"})
        self.assertIsNone(qs["other.prohibited_change"]["suggested"])   # 사용자 답은 AI 제안이 아니다
        self.assertIsNone(qs["other.bus_lane_violation"]["suggested"])

    def test_answers_become_user_facts(self):
        facts = catalog.answers_to_facts({"other.signal_delay": "예", "me.gross_negligence": "아니요", "other.slow_failure": "잘 모르겠어요"})
        by = {(f["actor"], f["factor"]): f for f in facts}
        self.assertEqual(by[("B", "signal_delay")]["value"], "있음")
        self.assertEqual(by[("A", "gross_negligence")]["value"], "없음")
        self.assertEqual(by[("B", "slow_failure")]["value"], "미확인")
        self.assertTrue(all(f["status"] == "user" for f in facts))

    def test_bad_answers_are_rejected(self):
        for bad in ({"x.signal_delay": "예"}, {"other.": "예"}, {"other.signal_delay": "네"}):
            with self.assertRaises(ValueError):
                catalog.answers_to_facts(bad)


if __name__ == "__main__":
    unittest.main()
