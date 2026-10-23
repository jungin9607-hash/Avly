"""가감요소 규칙의 '확인한 유형만 켜기'와 검수 현황 도구 시험."""

import unittest

from app import review_status
from avly.tables import ALL_ADJUSTMENT_RULES, active_rules, type_is_reviewed


def rule(reviewed=None, pdf=True):
    r = {"id": "x", "actor": "A", "factor": "f", "delta_pp": 10, "group": "g"}
    if pdf:
        r["pdf_source"] = {"chart": "차1-1", "raw_text": "A f +10"}
    if reviewed is not None:
        r["reviewed"] = reviewed
    return r


def config(reviewed=None, rules=None, **extra):
    c = {"rules": rules if rules is not None else [rule(False)], **extra}
    if reviewed is not None:
        c["reviewed"] = reviewed
    return c


class GateTests(unittest.TestCase):
    def test_a_type_is_on_when_its_type_is_marked_or_every_rule_is_marked(self):
        self.assertTrue(type_is_reviewed(config(True)))
        self.assertTrue(type_is_reviewed(config(False, [rule(True), rule(True)])))   # 규칙마다 확인 표시를 한 경우도 인정한다
        self.assertFalse(type_is_reviewed(config(False)))
        self.assertFalse(type_is_reviewed(config(False, [rule(True), rule(False)])))   # 일부만 확인했으면 켜지 않는다

    def test_types_entered_by_hand_before_review_marks_existed_stay_on(self):
        self.assertTrue(type_is_reviewed({"rules": [rule(None, pdf=False)]}))

    def test_only_reviewed_types_are_used_when_review_is_required(self):
        allr = {"1": config(False), "2": config(True), "3": {"rules": [rule(None, pdf=False)]}}
        self.assertEqual(sorted(active_rules(allr, True)), ["2", "3"])
        self.assertEqual(sorted(active_rules(allr, False)), ["1", "2", "3"])

    def test_with_the_real_data_only_the_original_seven_are_on_until_someone_reviews(self):
        on = active_rules(ALL_ADJUSTMENT_RULES, True)
        newly_reviewed = {k for k, t in ALL_ADJUSTMENT_RULES.items() if any("pdf_source" in r for r in t["rules"]) and type_is_reviewed(t)}
        self.assertEqual(set(on), {"1", "3", "11", "21", "27", "126", "128"} | newly_reviewed)


class StatusTests(unittest.TestCase):
    def summary(self, rules):
        return review_status.summarize(rules, {"a": {"reviewed": True}, "b": {"reviewed": False}}, {"places": {"p": {"reviewed": True}}})

    def test_counts_people_and_on_types(self):
        rules = {"1": config(True, reviewed_by="김", reviewed_at="2026-10-21"), "2": config(True, reviewed_by="김", reviewed_at="2026-10-21"),
                 "3": config(True, reviewed_by="이", reviewed_at="2026-10-21"), "4": config(False), "5": {"rules": [rule(None, pdf=False)]}}
        s = self.summary(rules)
        self.assertEqual((s["rules"]["pdf_types"], s["rules"]["pdf_types_done"]), (4, 3))
        self.assertEqual({k: len(v) for k, v in s["rules"]["by_person"].items()}, {"김": 2, "이": 1})
        self.assertEqual(s["rules"]["on_in_service"], [1, 2, 3, 5])
        self.assertEqual(s["easy_words"], {"total": 2, "done": 1})
        self.assertEqual(s["warnings"], [])

    def test_wrong_marks_are_flagged(self):
        rules = {"1": config(True),                                        # 검수자 없음
                 "2": config(False, [rule(True), rule(True)]),             # 규칙만 표시, 유형 표시 없음
                 "3": config(False, reviewed_by="김"),                      # 이름만 있고 완료 아님
                 "4": config(False, [rule(True), rule(False)])}            # 일부만
        s = self.summary(rules)
        text = " ".join(s["warnings"])
        self.assertIn("1번 유형: 확인 완료인데 검수자", text)
        self.assertIn("2번 유형: 규칙은 모두 확인 표시", text)
        self.assertIn("3번 유형: 검수자 이름은 있는데", text)
        self.assertEqual(s["rules"]["partial"], [("4", 1, 2)])

    def test_the_report_is_readable(self):
        text = review_status.render(self.summary({"1": config(True, reviewed_by="김", reviewed_at="2026-10-21")}))
        self.assertIn("확인 완료 1 / 1개 유형", text)
        self.assertIn("김 1개", text)


if __name__ == "__main__":
    unittest.main()
