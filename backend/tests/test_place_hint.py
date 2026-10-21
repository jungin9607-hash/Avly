"""사용자가 고른 장소 종류가 과실표의 장소 번호와 맞는지, 후보 개수 한도가 바뀌는지 확인한다. (AI 를 부르지 않는다)"""
import csv
import unittest
from pathlib import Path

from avly import matching
from avly.constants import PLACE_GROUPS
from avly.context import ctx

TABLE = Path(__file__).resolve().parents[1] / "model" / "avly" / "data" / "fault_table_car_to_car.csv"


class PlaceHintTests(unittest.TestCase):
    def tearDown(self):
        ctx.place_hint = False

    def test_every_group_matches_table_places(self):
        names = {}
        for row in csv.DictReader(TABLE.open(encoding="utf-8-sig")):
            names.setdefault(int(row["accident_place"]), row["accident_place_name"])
        self.assertEqual(sorted(c for codes in PLACE_GROUPS.values() for c in codes), sorted(names))
        self.assertIn("주차장", names[PLACE_GROUPS["주차장"][0]])
        self.assertEqual(names[PLACE_GROUPS["차도와 차도가 아닌 장소"][0]], "차도와 차도가 아닌 장소")

    def test_candidate_limit_grows_only_with_a_place(self):
        ctx.place_hint = False
        self.assertEqual(matching.candidate_limit(), 2)
        ctx.place_hint = True
        self.assertEqual(matching.candidate_limit(), 4)

    def test_place_is_not_second_guessed_when_chosen(self):
        class Scene:
            road_shape = "교차로"
        ctx.place_hint = True
        self.assertTrue(matching.place_compatible({"accident_place_name": "주차장(또는 차도가 아닌 장소)", "accident_place": 5}, Scene()))
