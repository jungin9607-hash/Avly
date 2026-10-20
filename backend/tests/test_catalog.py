import unittest

from app import catalog


class CatalogTests(unittest.TestCase):
    def test_loads_133_car_to_car_types(self):
        rows = catalog.rows()
        self.assertEqual(len(rows), 133)
        self.assertEqual(sorted(rows)[0], 0)
        self.assertEqual(sorted(rows)[-1], 132)

    def test_options_are_unique_by_the_four_visible_items_and_sum_to_100(self):
        options = catalog.options()
        labels = [(o["place"], o["feature"], o["my_progress"], o["other_progress"]) for o in options]
        self.assertEqual(len(labels), len(set(labels)))   # 화면에서 네 항목을 고르면 선택지가 하나로 정해진다
        for o in options:
            self.assertEqual(o["base_me"] + o["base_other"], 100)
        self.assertEqual(len(options), 261)

    def test_every_type_is_reachable(self):
        reachable = {o["accident_type_id"] for o in catalog.options()}
        # 114번과 116번은 같은 상황이라 번호가 작은 114번만 남는다. 그 밖의 유형은 모두 고를 수 있다.
        self.assertEqual(set(catalog.rows()) - reachable, {116})

    def test_symmetric_types_appear_once(self):
        ids = [o["accident_type_id"] for o in catalog.options()]
        self.assertEqual(ids.count(6), 1)    # 마주 보며 직진, 50:50
        self.assertEqual(ids.count(12), 1)   # 동시 차로변경, 50:50

    def test_orientation_swaps_progress_and_fault(self):
        row = catalog.get_row(11)
        a, b = catalog.orient(row, "A"), catalog.orient(row, "B")
        self.assertEqual((a["my_progress"], a["other_progress"]), ("후행 직진", "선행 진로변경"))
        self.assertEqual((a["base_me"], a["base_other"]), (30, 70))
        self.assertEqual((b["my_progress"], b["other_progress"]), ("선행 진로변경", "후행 직진"))
        self.assertEqual((b["base_me"], b["base_other"]), (70, 30))

    def test_every_name_in_the_table_has_an_easy_label(self):
        """과실표에 있는 모든 장소·특징·진행 이름에 쉬운 말이 있고, 쉬운 파일에 남는(없는 이름) 항목이 없다."""
        rows = catalog.rows().values()
        names = {
            "places": {r.place for r in rows},
            "features": {r.feature for r in rows},
            "progress": {r.a_progress for r in rows} | {r.b_progress for r in rows},
        }
        for kind, expected in names.items():
            entries = catalog.labels()[kind]
            self.assertEqual(set(entries), expected, kind)
            for name, entry in entries.items():
                self.assertTrue(entry["easy"].strip(), name)
                self.assertIn("reviewed", entry)

    def test_orient_adds_easy_names_and_keeps_the_original_ones(self):
        a = catalog.orient(catalog.get_row(11), "A")
        self.assertEqual((a["feature"], a["my_progress"]), ("차로변경(진로변경)", "후행 직진"))   # 원래 이름은 그대로
        self.assertEqual(a["easy"]["feature"], "차선 변경 사고")
        self.assertEqual(a["easy"]["my_progress"], "뒤따르던 차가 직진")
        self.assertEqual(a["easy"]["other_progress"], "앞서가던 차가 차선 변경")

    def test_missing_easy_label_falls_back_to_the_original_name(self):
        self.assertEqual(catalog.easy_label("feature", "없는 이름"), "없는 이름")

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
