import unittest

from avly import law

PROFILE = {"type": 107, "text": "T자형 교차로 좌회전", "groups": [("좌회전", ["좌회전"]), ("교차로", ["교차로"])], "queries": ["좌회전", "교차로"]}


def body(number="2022나12345", title="손해배상(자)", text="교차로에서 교통사고가 발생했고 쌍방의 과실 비율이 쟁점이다.", **extra):
    return {"사건번호": number, "사건명": title, "판시사항": "", "판결요지": text, "판례내용": text, "법원명": "서울중앙지방법원",
            "선고일자": "20220101", "판례정보일련번호": "1", **extra}


class PartialMatchTests(unittest.TestCase):
    def test_partial_case_is_marked_and_lists_matched_conditions(self):
        c = law.match_case_body_partial(body(), PROFILE)
        self.assertEqual(c["relevance_status"], "partial_reference")
        self.assertEqual(c["matched_terms"], ["교차로"])
        self.assertIn("1/2개 조건", c["comparison_limit"])
        self.assertIn("검색 일치 조건: 교차로", c["comparison_limit"])

    def test_criminal_case_is_never_used(self):
        self.assertIsNone(law.match_case_body_partial(body(number="2023노1354", title="교통사고처리특례법위반"), PROFILE))

    def test_case_without_any_matching_condition_is_dropped(self):
        self.assertIsNone(law.match_case_body_partial(body(text="고속도로에서 교통사고가 발생해 과실을 다투었다."), PROFILE))

    def test_parking_lot_condition_is_required(self):
        profile = {**PROFILE, "groups": [("주차장", ["주차장"]), ("출차", ["출차"])], "text": "주차장 출차"}
        self.assertIsNone(law.match_case_body_partial(body(text="교차로에서 출차하던 차량과 충돌한 교통사고의 과실"), profile))
        self.assertIsNotNone(law.match_case_body_partial(body(text="주차장 통로에서 교통사고가 났고 과실을 다투었다."), profile))


class RelatedCasesFillTests(unittest.TestCase):
    class Client:
        def __init__(self, bodies):
            self.bodies = bodies

        def search(self, query):
            return [{"판례일련번호": str(i), "사건번호": b["사건번호"]} for i, b in self.bodies.items()] if query == "좌회전" else []

        def detail(self, identifier):
            return self.bodies[int(identifier)]

    ROW = {"accident_type": 107, "accident_place_name": "T자형 교차로", "accident_place_feature_name": "동일폭 도로",
           "vehicle_a_progress_info_name": "왼쪽 도로에서 직진", "vehicle_b_progress_info_name": "오른쪽 도로에서 좌회전", "accident_object_name": "차대차"}

    def test_partial_cases_fill_up_to_three_best_first(self):
        bodies = {i: body(number=f"2022나{i}", text="교차로에서 교통사고가 발생해 과실을 다투었다." + ("좌회전 차량이 있었다." if i == 3 else "")) for i in (1, 2, 3, 4)}
        cases, audit = law.related_cases_for_row(self.ROW, client=self.Client(bodies))
        self.assertEqual(len(cases), 3)
        self.assertEqual(cases[0]["case_number"], "2022나3")   # 조건을 더 많이 만족한 판례가 앞
        self.assertEqual(audit["status"], "ok")
        self.assertTrue(all(c["relevance_status"] == "partial_reference" for c in cases))

    def test_still_insufficient_when_nothing_matches(self):
        cases, audit = law.related_cases_for_row(self.ROW, client=self.Client({1: body(text="무관한 내용")}))
        self.assertEqual((len(cases), audit["status"]), (0, "insufficient"))


class SearchQueryTests(unittest.TestCase):
    def test_combined_queries_come_before_single_words(self):
        queries = law.case_search_queries(PROFILE)
        self.assertEqual(queries[0], "좌회전 교차로 과실")
        self.assertEqual(queries[-2:], ["좌회전", "교차로"])
        self.assertEqual(len(queries), len(set(queries)))
