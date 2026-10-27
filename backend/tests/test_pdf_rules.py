"""PDF(손해보험협회 인정기준 2023.06)에서 합친 가감요소 규칙 시험. 규칙 데이터가 과실표와 맞는지, 엔진이 새 규칙을 다루는지 본다."""

import csv
import unittest

from app import catalog
from avly import explain
from avly.adjustments import evaluate_rule_input
from avly.tables import ADJUSTMENT_RULES, FACTOR_LABELS

BLOCKED = {2, 55, 56, 57, 79, 86, 87, 88, 120, 123, 127}   # PDF 와 CSV 의 기본 비율·조건이 달라 일부러 등록하지 않은 유형
DELETED = {38, 39, 41, 42, 89}   # 검수 결정(2026-10-22)으로 지운 유형: PDF 에 해당 가감요소가 없다. 38·39·41·42 는 이름에 선진입/후진입이 이미 들어 있는데 '명확한 선진입' 가감이 또 붙어 있었고, 89 는 가감 항목의 차량 대응이 맞지 않았다
PENDING_REVIEW = {0, 4, 8, 25, 26, 107, 108}               # 원문에서 역할·수치가 불분명한 항목이 남은 유형


def scenario(type_id, role="A"):
    row = catalog.get_row(type_id)
    option = catalog.orient(row, role)
    return {"scenario_id": f"{type_id}:{role}", "accident_type": type_id, "dashcam_table_role": role, "eligible_for_adjustment": True,
            "base_fault": {"A": option["base_me"], "B": option["base_other"]}, "table_progress": {"A": row.a_progress, "B": row.b_progress}}


def evaluate(type_id, answers=(), role="A"):
    """answers: [(actor 'A'|'B'=서비스 기준, factor, '있음'|'없음')]. 사용자 답으로 계산한다."""
    factors = [{"actor": a, "factor": f, "value": v, "status": "user"} for a, f, v in answers]
    return evaluate_rule_input({"scenarios": [scenario(type_id, role)], "factors": factors})["results"][0]


class DataTests(unittest.TestCase):
    def test_coverage_grew_from_7_to_117_types_and_blocked_or_deleted_types_stay_out(self):
        registered = {int(k) for k in ADJUSTMENT_RULES}
        self.assertEqual(len(registered), 117)
        self.assertEqual(registered & (BLOCKED | DELETED), set())
        self.assertEqual(registered | BLOCKED | DELETED, set(range(133)))

    def test_every_registered_type_matches_the_fault_table(self):
        for key, config in ADJUSTMENT_RULES.items():
            row = catalog.get_row(int(key))
            self.assertEqual(config["expected_base"], [row.negligence_a, row.negligence_b], key)
            self.assertEqual((config["expected_a_progress"], config["expected_b_progress"]), (row.a_progress, row.b_progress), key)

    def test_every_factor_has_a_label_and_an_explained_question(self):
        for key, config in ADJUSTMENT_RULES.items():
            for rule in config["rules"]:
                self.assertIn(rule["factor"], FACTOR_LABELS, (key, rule["factor"]))
                for who in ("내 차", "상대 차"):
                    e = explain.explain_factor(rule["factor"], rule["delta_pp"], who)
                    self.assertFalse(e["missing"], (key, rule["factor"]))
                    self.assertTrue(e["question"].endswith("?"), (key, rule["factor"]))

    def test_rule_ids_are_unique_within_a_type(self):
        for key, config in ADJUSTMENT_RULES.items():
            ids = [r["id"] for r in config["rules"]]
            self.assertEqual(len(ids), len(set(ids)), key)

    def test_the_seven_original_types_keep_their_original_rules(self):
        self.assertEqual(len(ADJUSTMENT_RULES["11"]["rules"]), 8)
        self.assertIn("t_intersection_turn", {r["factor"] for r in ADJUSTMENT_RULES["27"]["rules"]})   # 새 PDF 규칙에는 빠져 있던 항목
        signal = next(r for r in ADJUSTMENT_RULES["11"]["rules"] if r["factor"] == "signal_delay")
        self.assertFalse(signal.get("manual_only"))   # 영상 관찰로 자동 적용되는 기존 동작을 보존한다


class QuestionTests(unittest.TestCase):
    def test_question_keys_are_unique_for_every_registered_type_and_role(self):
        for key in ADJUSTMENT_RULES:
            for role in ("A", "B"):
                keys = [q["key"] for q in catalog.adjustment_questions(int(key), role)]
                self.assertEqual(len(keys), len(set(keys)), (key, role))   # 같은 키가 두 번 나오면 사용자 답변이 섞인다

    def test_new_type_asks_each_registered_item_in_easy_words(self):
        questions = catalog.adjustment_questions(60, "A")
        self.assertGreaterEqual(len(questions), 3)
        for q in questions:
            self.assertTrue(q["question"].endswith("?"))
            self.assertTrue(q["needs_user"])   # PDF 규칙은 사용자가 직접 확인한다
            self.assertNotIn("pdf_", q["title"])


class EngineTests(unittest.TestCase):
    def test_new_type_waits_for_answers_then_applies_the_confirmed_item(self):
        out = evaluate(0)
        self.assertTrue(out["pending"])
        self.assertIsNone(out["final_fault"])
        config = ADJUSTMENT_RULES["60"]
        out = evaluate(60)
        self.assertEqual(len(out["pending"]), len(config["rules"]))
        item = next(r for r in config["rules"] if r["actor"] == "A")
        base_a = out["base_fault"]["A"]
        answered = evaluate(60, [("A", item["factor"], "있음")])
        self.assertEqual(answered["applied_adjustments"][0]["rule_id"], item["id"])
        self.assertEqual(answered["adjusted_fault"]["A"], max(0, min(100, base_a + item["delta_pp"])))

    def test_all_answered_no_gives_a_final_ratio_for_a_type_without_pending_review(self):
        config = ADJUSTMENT_RULES["60"]
        self.assertNotIn(60, PENDING_REVIEW)
        answers = [({"A": "A", "B": "B"}[r["actor"]], r["factor"], "없음") for r in config["rules"]]
        out = evaluate(60, answers)
        self.assertEqual(out["final_fault"], out["base_fault"])
        self.assertEqual(out["pending"], [])

    def test_types_with_unclear_source_items_never_get_a_final_ratio(self):
        for type_id in sorted(PENDING_REVIEW):
            config = ADJUSTMENT_RULES[str(type_id)]
            answers = [(r["actor"], r["factor"], "없음") for r in config["rules"]]
            out = evaluate(type_id, answers)
            self.assertEqual(out["pending"], [], type_id)
            self.assertIsNone(out["final_fault"], type_id)
            self.assertTrue(out["source_review_pending"], type_id)
            self.assertIn("원문 항목 추가 검토", out["status"], type_id)

    def test_answers_that_contradict_each_other_are_asked_again(self):
        # 같은 exclusive 그룹(서행 불이행 / 서행 또는 일시정지)에서 서로 다른 요소에 모두 '있음'
        for key, config in ADJUSTMENT_RULES.items():
            by_group = {}
            for r in config["rules"]:
                by_group.setdefault(r["group"], []).append(r)
            group = next((g for g in config.get("exclusive_groups", []) if len({r["factor"] for r in by_group.get(g, [])}) > 1), None)
            if group:
                break
        self.assertIsNotNone(group, "서로 양립하지 않는 항목이 있는 유형이 하나는 있어야 한다")
        picked = by_group[group][:2]
        out = evaluate(int(key), [(r["actor"], r["factor"], "있음") for r in picked])
        ids = {r["id"] for r in picked}
        self.assertEqual({x["rule_id"] for x in out["applied_adjustments"]} & ids, set())   # 어느 쪽도 적용하지 않는다
        self.assertTrue(ids <= {x["rule_id"] for x in out["pending"]})   # 다시 확인할 항목으로 돌아간다
        self.assertFalse(ids & {x["rule_id"] for x in out["not_applied"]})

    def test_result_is_kept_between_0_and_100(self):
        config = ADJUSTMENT_RULES["1"]
        answers = [(r["actor"], r["factor"], "있음") for r in config["rules"] if r["actor"] == "A"]
        out = evaluate(1, answers)
        self.assertTrue(0 <= out["adjusted_fault"]["A"] <= 100)


if __name__ == "__main__":
    unittest.main()
