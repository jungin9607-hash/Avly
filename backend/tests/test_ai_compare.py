import unittest
from unittest import mock
from uuid import uuid4

from app import catalog
from app.worker import ai_compare, finalize, runner
from app.worker.ai_compare import AiComparer, CaseAnalysis, Item, Point, Verdict, Verdicts
from tests.helpers import DbTestCase

BODY = ("선행 차량이 방향지시등을 켜지 않은 채 차로를 변경하다가 후행 직진 차량과 충돌한 사고이다. "
        "진로를 변경하는 차량은 뒤따르는 차량의 정상적인 통행을 방해하지 않을 주의의무가 있다. 도로교통법 제19조 및 제38조 참조.")
OPTION = catalog.orient(catalog.get_row(11), "A")


def case(**extra):
    return {"case_id": str(uuid4()), "court": "서울중앙지방법원", "case_number": "2022나12345", "title": "손해배상(자)",
            "summary": "요약", "relevance_status": "keyword_reference", "_text": BODY, **extra}


def item(label="방향지시등", text="상대 차가 신호 없이 차로를 바꾼 점이 같아요.", quote="방향지시등을 켜지 않은 채 차로를 변경하다가", kind="both"):
    return Item(label=label, text=text, quote=quote, kind=kind)


def analysis(common=None, differences=None, overview_quote="진로를 변경하는 차량은 뒤따르는 차량의 정상적인 통행을 방해하지 않을 주의의무가 있다"):
    return CaseAnalysis(overview=Point(text="진로변경 사고에 대한 판례예요.", quote=overview_quote),
                        ruling_points=[Point(text="진로변경 차량에게 주의의무가 있어요.", quote="정상적인 통행을 방해하지 않을 주의의무가 있다"),
                                       Point(text="지어낸 판단이에요.", quote="본문에 없는 문장입니다 정말로 없어요")],
                        common=common if common is not None else [item()], differences=differences or [])


class ValidateTests(unittest.TestCase):
    def test_keeps_items_whose_quote_is_in_the_case_text(self):
        out = ai_compare.validate(analysis(), BODY)
        self.assertEqual([i["label"] for i in out["common"]], ["방향지시등"])
        self.assertEqual(len(out["ruling_points"]), 1)   # 본문에 없는 구절을 인용한 판단은 버린다
        self.assertEqual(out["overview"]["text"], "진로변경 사고에 대한 판례예요.")

    def test_quote_matching_ignores_spacing(self):
        out = ai_compare.validate(analysis(common=[item(quote="방향지시등을   켜지 않은 채\n차로를 변경하다가")]), BODY)
        self.assertEqual(len(out["common"]), 1)

    def test_drops_items_with_invented_quote(self):
        out = ai_compare.validate(analysis(common=[item(quote="후행 차량이 급제동해서 충돌을 피했다고 인정했다")]), BODY)
        self.assertEqual((out["common"], out["differences"]), ([], []))

    def test_drops_ratio_and_outcome_words(self):
        for text in ("과실이 70% 로 정해졌어요.", "내 차가 유리해요.", "원고가 승소한 사건이에요.", "비율은 30:70 이에요."):
            self.assertEqual(ai_compare.validate(analysis(common=[item(text=text)]), BODY)["common"], [], text)

    def test_mine_only_needs_no_quote_but_case_only_does(self):
        out = ai_compare.validate(analysis(common=[], differences=[
            item(label="내 사고만", text="내 사고에서는 상대가 정지해 있었지만 판례 본문에서는 확인되지 않아요.", quote="", kind="mine_only"),
            item(label="단정", text="판례에서는 상대 차가 시속 60km로 달렸습니다.", quote="", kind="mine_only"),
            item(label="판례만", text="판례에는 제동 이야기가 있어요.", quote="제동을 했으나 충돌을 피하지 못했다", kind="case_only")]), BODY)
        self.assertEqual([d["label"] for d in out["differences"]], ["내 사고만"])
        self.assertEqual(out["differences"][0]["quote"], "")

    def test_irrelevant_quote_is_not_evidence(self):
        bad = item(text="양쪽 차량이 모두 시속 육십 킬로미터로 달렸어요.", quote="방향지시등을 켜지 않은 채 차로를 변경하다가")
        out = ai_compare.validate(analysis(common=[bad]), BODY)
        self.assertEqual(out["common"], [])

    def test_digest_is_kept_when_no_comparison_item_survives(self):
        out = ai_compare.validate(analysis(common=[item(quote="본문에 없는 구절을 인용했어요 정말로")]), BODY)
        self.assertEqual(out["common"], [])
        self.assertTrue(out["overview"])
        comparison = ai_compare.assemble(case(), OPTION, out)
        self.assertEqual(comparison["comparison"]["source"], "rule")   # 비교는 규칙으로
        self.assertTrue(comparison["digest"]["overview"])              # 판례 설명은 AI 로

    def test_kind_must_match_the_list(self):
        out = ai_compare.validate(analysis(common=[item(kind="case_only")]), BODY)
        self.assertEqual((out["common"], out["differences"]), ([], []))


class HelperTests(unittest.TestCase):
    def test_laws_are_taken_from_the_case_text(self):
        laws = ai_compare.laws_in(BODY + " 도로교통법 제19조")
        self.assertEqual([l["article"] for l in laws], ["19", "38"])
        self.assertEqual(laws[0]["label"], "도로교통법 제19조")
        # 다른 법의 조문은 섞지 않는다
        self.assertEqual([l["article"] for l in ai_compare.laws_in("도로교통법 제48조 및 민법 제750조, 제756조")], ["48"])

    def test_situation_text_lists_the_confirmed_answers(self):
        text = ai_compare.situation_text(OPTION, {"other.signal_delay": "예"})
        self.assertIn("후행 직진", text)
        self.assertIn("상대 차", text)
        self.assertIn("예", text)


def fake_ask(first, supported=None, calls=None):
    """첫 호출(CaseAnalysis)에는 first 를, 두 번째 호출(Verdicts)에는 supported 에 든 id 만 true 로 답하는 가짜 ask."""
    def ask(model, instructions, text, schema, *args, **kwargs):
        if calls is not None:
            calls.append(schema.__name__)
        if schema is CaseAnalysis:
            return first, {"input_tokens": 10, "output_tokens": 5}
        ids = [int(n) for n in __import__("re").findall(r"^\[(\d+)\]", text, flags=__import__("re").M)]
        keep = set(ids) if supported is None else set(supported)
        return Verdicts(items=[Verdict(id=n, supported=n in keep) for n in ids]), {}
    return ask


class VerifyTests(unittest.TestCase):
    def test_unsupported_items_are_removed(self):
        payload = ai_compare.validate(analysis(differences=[item(label="반대", text="판례에서는 차로가 구분되어 있었어요.", kind="case_only",
                                                                   quote="방향지시등을 켜지 않은 채 차로를 변경하다가")]), BODY)
        claims = ai_compare._claims(payload)
        keep = {n for n, (kind, e) in enumerate(claims) if e.get("label") != "반대"}
        out = ai_compare.apply_verdicts(payload, keep)
        self.assertEqual([i["label"] for i in out["common"]], ["방향지시등"])
        self.assertEqual(out["differences"], [])
        self.assertTrue(out["overview"])

    def test_nothing_left_returns_none(self):
        payload = ai_compare.validate(analysis(), BODY)
        self.assertIsNone(ai_compare.apply_verdicts(payload, set()))


class AiComparerTests(DbTestCase):
    def setUp(self):
        super().setUp()
        from app.repository import Repository
        self.repo = Repository(self.engine)
        self.case_id = self.repo.upsert_case({
            "court": "서울중앙지방법원", "decided_on": None, "case_number": "2022나12345", "title": "t", "summary": "s",
            "fault_ratio": None, "source_kind": "law_api", "source_url": None, "verified": False, "verified_by": None,
            "verified_at": None, "raw": {}, "fetched_at": None})

    def comparer(self, ask):
        return AiComparer(self.repo, ask=ask, model="test-model")

    def test_result_is_validated_and_cached(self):
        calls = []
        ask = fake_ask(analysis(), calls=calls)
        c = case(case_id=str(self.case_id))
        first = self.comparer(ask).compare_all([c], OPTION, {})
        second = self.comparer(ask).compare_all([c], OPTION, {})
        self.assertEqual(calls, ["CaseAnalysis", "Verdicts"])   # 비교 한 번 + 검증 한 번. 두 번째는 DB 에 저장한 결과를 쓴다
        self.assertEqual(first, second)
        comparison = first[c["case_id"]]["comparison"]
        self.assertEqual((comparison["source"], comparison["match_level"]), ("ai", "partial"))
        self.assertEqual(comparison["common_items"][0]["quote"], "방향지시등을 켜지 않은 채 차로를 변경하다가")
        self.assertEqual([l["article"] for l in first[c["case_id"]]["digest"]["laws"]], ["19", "38"])

    def test_different_situation_is_not_served_from_cache(self):
        calls = []
        ask = fake_ask(analysis(), calls=calls)
        c = case(case_id=str(self.case_id))
        self.comparer(ask).compare_all([c], OPTION, {})
        self.comparer(ask).compare_all([c], OPTION, {"other.signal_delay": "예"})
        self.assertEqual(calls.count("CaseAnalysis"), 2)

    def test_falls_back_to_rules_when_the_call_fails(self):
        c = case(case_id=str(self.case_id))
        out = self.comparer(mock.Mock(side_effect=RuntimeError("boom"))).compare_all([c], OPTION, {})
        self.assertEqual(out[c["case_id"]]["comparison"]["source"], "rule")
        self.assertIsNone(out[c["case_id"]]["digest"])

    def test_falls_back_when_nothing_survives_validation(self):
        c = case(case_id=str(self.case_id))
        bad = analysis(common=[item(quote="본문에 없는 구절을 인용했어요 정말로")]).model_copy(update={
            "overview": Point(text="개요", quote="본문에 없는 개요 구절이에요 정말로"), "ruling_points": []})
        out = self.comparer(fake_ask(bad)).compare_all([c], OPTION, {})
        self.assertEqual(out[c["case_id"]]["comparison"]["source"], "rule")
        self.assertEqual(self.repo.get_case_ai("x" * 64), None)

    def test_items_rejected_by_the_second_check_never_reach_the_result(self):
        c = case(case_id=str(self.case_id))
        out = self.comparer(fake_ask(analysis(), supported=[])).compare_all([c], OPTION, {})   # 검증이 전부 거부
        self.assertEqual(out[c["case_id"]]["comparison"]["source"], "rule")
        self.assertIsNone(out[c["case_id"]]["digest"])
        self.assertIsNone(self.repo.get_case_ai(self.comparer(None)._key(c, ai_compare.situation_text(OPTION, {}))))   # 거부된 결과는 저장하지 않는다

    def test_one_line_registered_summary_is_not_sent(self):
        ask = mock.Mock()
        c = case(case_id=str(self.case_id), _text="지하주차장에서 후진 출차 차량이 통로 진행 차량의 옆부분을 충격한 사례. 출차 차량의 과실이 인정된 것으로 소개됨.")
        out = self.comparer(ask).compare_all([c], OPTION, {})
        ask.assert_not_called()
        self.assertEqual(out[c["case_id"]]["comparison"]["source"], "rule")

    def test_finalize_uses_comparisons_and_hides_source_text(self):
        c = case(case_id=str(self.case_id), relevance_status="civil_traffic_context_reference")
        comparisons = self.comparer(fake_ask(analysis())).compare_all([c], OPTION, {})
        snapshot = {"situation": {"summary": "s", "candidates": []}, "timeline": [], "impact": {}}
        result = finalize.build_result(snapshot, {"accident_type_id": 11, "role": "A", "answers": {}}, [c], comparisons)
        related = result["related_cases"][0]
        self.assertNotIn("_text", related)
        self.assertEqual(related["comparison"]["source"], "ai")
        self.assertIn("overview", related["digest"])
        # AI 결과가 없으면 규칙 비교가 붙는다
        rule = finalize.build_result(snapshot, {"accident_type_id": 11, "role": "A", "answers": {}}, [c])["related_cases"][0]
        self.assertEqual(rule["comparison"]["source"], "rule")
        self.assertNotIn("digest", rule)


class MakeComparerTests(unittest.TestCase):
    def make(self, mode, engine="avly", key="k"):
        from app.config import settings
        env = {"OPENAI_API_KEY": key} if key else {}
        with mock.patch.object(type(settings), "__setattr__", object.__setattr__), \
                mock.patch.dict("os.environ", env, clear=False), \
                mock.patch("app.config.settings", mock.Mock(case_compare=mode, engine=engine)):
            if not key:
                import os
                os.environ.pop("OPENAI_API_KEY", None)
            return ai_compare.make_comparer(mock.Mock())

    def test_auto_uses_ai_only_with_real_engine_and_key(self):
        self.assertIsNotNone(self.make("auto"))
        self.assertIsNone(self.make("auto", engine="fake"))

    def test_rule_never_uses_ai(self):
        self.assertIsNone(self.make("rule"))

    def test_ai_forces_ai(self):
        self.assertIsNotNone(self.make("ai", engine="fake"))


if __name__ == "__main__":
    unittest.main()
