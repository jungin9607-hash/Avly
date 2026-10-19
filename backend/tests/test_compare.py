import unittest

from app import catalog
from app.worker import compare


def option(type_id=126, role="A"):
    return catalog.orient(catalog.get_row(type_id), role)


REGISTERED = {
    "relevance_status": "registered_chart_reference",
    "summary": "지하주차장에서 후진 출차 차량이 통로 진행 차량의 옆부분을 충격한 사례. 출차 차량의 과실 100%가 인정된 것으로 소개됨.",
    "comparison_limit": "후진 출차 사례이며, 현재 영상의 출차 여부·진행 방향이 미확인이므로 같은 비율을 적용하지 않음.",
}
FOUND = {
    "relevance_status": "civil_traffic_context_reference",
    "summary": "주차장에서 출차하던 차량과 통로를 진행하던 차량이 충돌한 사고에서 쌍방의 과실을 따졌다.",
    "comparison_limit": "검색 일치 조건: 주차장 / 출차; 신호·진행·접촉 위치·위반 사정이 실제 영상과 같은지는 별도 검토가 필요하며 비율을 자동 적용하지 않음.",
}


class CompareTests(unittest.TestCase):
    def test_registered_case_is_same_type_and_keeps_its_limit_first(self):
        c = compare.compare_case(REGISTERED, option())
        self.assertEqual((c["match_level"], c["match_label"]), ("same_type", "같은 사고 유형"))
        self.assertIn("손해보험협회 도표", c["common"][0])
        self.assertEqual(c["differences"][0], REGISTERED["comparison_limit"])
        self.assertEqual(c["note"], compare.NOTE)

    def test_keyword_overlap_goes_to_common_and_the_rest_to_differences(self):
        c = compare.compare_case(REGISTERED, option())   # 내 사고: 통로 직진 / 주차구역에서 직진 출차
        self.assertTrue(any("'출차'" in x and "모두" in x for x in c["common"]))
        self.assertTrue(any("'후진'" in x and "판례에는" in x for x in c["differences"]))   # 판례는 후진 출차, 내 사고는 직진 출차
        self.assertFalse(any("'직진'" in x and "판례에는" in x for x in c["differences"]))

    def test_found_case_is_partial_and_lists_matched_conditions(self):
        c = compare.compare_case(FOUND, option())
        self.assertEqual(c["match_level"], "partial")
        self.assertIn("판결 본문에서 '주차장' 조건이 확인돼요.", c["common"])
        self.assertIn("판결 본문에서 '출차' 조건이 확인돼요.", c["common"])
        self.assertEqual(c["differences"][0], "신호, 진행 방식, 접촉 위치가 실제 영상과 같은지는 별도 확인이 필요해요.")

    def test_lists_are_capped_and_deduplicated(self):
        case = {**REGISTERED, "summary": "후진 전진 출차 직진 좌회전 우회전 진로변경 추돌 정차 주차 교차로 합류 역주행 중앙선"}
        c = compare.compare_case(case, option())
        self.assertLessEqual(len(c["common"]), compare.MAX_ITEMS)
        self.assertLessEqual(len(c["differences"]), compare.MAX_ITEMS)
        self.assertEqual(len(c["common"]), len(set(c["common"])))

    def test_always_has_a_difference_and_a_common_point(self):
        c = compare.compare_case({"relevance_status": "civil_traffic_context_reference", "summary": ""}, option(11))
        self.assertTrue(c["common"] and c["differences"])
        self.assertIn("교통사고 판결 본문", c["common"][0])

    def test_no_percentage_is_ever_produced(self):
        for case in (REGISTERED, FOUND):
            text = " ".join(compare.compare_case(case, option())["common"] + compare.compare_case(case, option())["differences"])
            self.assertNotIn("%", text.replace("과실 100%가", ""))


if __name__ == "__main__":
    unittest.main()
