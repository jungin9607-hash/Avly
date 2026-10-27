import json
import unittest
from pathlib import Path

from app.situation_check import situation_check, table_group


def option(my, other):
    return {"my_progress": my, "other_progress": other, "easy": {"my_progress": f"쉬운 {my}", "other_progress": f"쉬운 {other}"}}


class TableGroupTests(unittest.TestCase):
    def test_reads_one_action_from_table_phrases(self):
        for phrase, group in {
            "후행 직진": "straight", "[녹색신호] 직진, [적색신호] 충돌": "straight", "직진(교차로 내 진로변경)": "straight",
            "선행 진로변경": "lane_change", "동시 차로변경(진로변경)": "lane_change", "차로 감소 도로에서 본선으로 합류": "lane_change",
            "(마주보며) [녹색신호] 좌회전 (비보호 좌회전)": "left", "일시정지 위반 우회전": "right", "급 유턴(후행)": "uturn",
            "후행 추돌": "straight", "주(정)차": "stopped", "주차구역에서 후진 출차": None,
        }.items():
            self.assertEqual(table_group(phrase), group, phrase)

    def test_unreadable_or_mixed_phrases_are_unknown(self):
        for phrase in ("정차 후 출발", "교차로 내 회전", "선행 자동차(1차사고차량)", "주차구역에서 직진 출차", "", None):
            self.assertIsNone(table_group(phrase), phrase)

    def test_every_registered_phrase_is_handled(self):
        labels = json.loads((Path(__file__).resolve().parents[1] / "app" / "data" / "accident_labels.json").read_text(encoding="utf-8"))
        groups = {phrase: table_group(phrase) for phrase in labels["progress"]}
        self.assertEqual(len(groups), 146)
        self.assertGreater(sum(1 for g in groups.values() if g), 100)   # 대부분은 동작 하나로 읽힌다


class SituationCheckTests(unittest.TestCase):
    def test_conflict_when_chosen_action_differs_from_what_ai_saw(self):
        out = situation_check("직진", "정지/대기", option("후행 직진", "선행 진로변경"))
        self.assertTrue(out["conflict"])
        self.assertEqual(out["items"], [{"who": "other", "ai_action": "정지/대기", "chosen": "쉬운 선행 진로변경"}])

    def test_both_sides_can_conflict(self):
        out = situation_check("좌회전", "직진", option("직진", "우회전"))
        self.assertEqual([i["who"] for i in out["items"]], ["me", "other"])

    def test_same_action_is_not_a_conflict(self):
        out = situation_check("직진", "진로변경", option("후행 직진", "선행 진로변경"))
        self.assertEqual(out, {"conflict": False, "items": []})

    def test_stopped_front_car_is_compatible_with_going_straight(self):
        self.assertFalse(situation_check("직진", "정지/대기", option("후행 추돌", "선행 직진"))["conflict"])

    def test_unknown_ai_or_table_wording_never_conflicts(self):
        self.assertFalse(situation_check("미확인", "기타", option("직진", "좌회전"))["conflict"])
        self.assertFalse(situation_check(None, None, option("직진", "좌회전"))["conflict"])
        self.assertFalse(situation_check("직진", "직진", option("교차로 내 회전", "정차 후 출발"))["conflict"])


if __name__ == "__main__":
    unittest.main()
