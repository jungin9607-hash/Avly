import json
import unittest
from pathlib import Path

from app.worker import snapshot

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / f"model_result_{name}.json").read_text(encoding="utf-8"))


class SnapshotTests(unittest.TestCase):
    def test_lane_change_snapshot(self):
        snap = snapshot.from_model_result(load("lane_change"), "replay")
        s = snap["situation"]
        self.assertEqual(snap["accident_object"], "차대차")
        self.assertEqual(len(s["candidates"]), 1)
        c = s["candidates"][0]
        self.assertEqual((c["accident_type_id"], c["role"], c["source"], c["eligible"]), (11, "A", "matched", True))
        self.assertEqual((c["my_progress"], c["other_progress"], c["base_me"], c["base_other"]), ("후행 직진", "선행 진로변경", 30, 70))
        self.assertEqual(s["default_index"], 0)
        self.assertEqual(s["my_action"], "직진")
        self.assertEqual(s["other_action"], "진로변경")

    def test_impact_time_comes_from_the_anchor_frame(self):
        data = load("lane_change")
        snap = snapshot.from_model_result(data, "replay")
        frames = {f["id"]: f["sec"] for f in data["overview_frames"] + data["review_frames"]}
        self.assertEqual(snap["impact"]["sec"], frames[data["scene"]["impact_anchor_frame_id"]])
        self.assertEqual(snap["impact"]["contact"], "충돌 정황 강함")
        self.assertTrue(snap["impact"]["confirmed"])
        self.assertEqual(snap["situation"]["needs_check"], [])

    def test_unconfirmed_contact_is_flagged(self):
        data = load("lane_change")
        data["scene"]["contact"] = "접촉 추정"
        snap = snapshot.from_model_result(data, "replay")
        self.assertFalse(snap["impact"]["confirmed"])
        self.assertEqual(snap["situation"]["needs_check"], ["직접 접촉 장면은 영상에서 확인되지 않았습니다."])

    def test_reference_only_candidates_are_not_preselected(self):
        snap = snapshot.from_model_result(load("parking"), "replay")
        s = snap["situation"]
        self.assertEqual([c["source"] for c in s["candidates"]], ["reference", "reference"])
        self.assertEqual({c["accident_type_id"] for c in s["candidates"]}, {126, 127})
        self.assertTrue(all(not c["eligible"] for c in s["candidates"]))
        self.assertIsNone(s["default_index"])
        self.assertEqual(snap["situation"]["road_shape"], "주차장")

    def test_no_candidates_asks_the_user_to_choose(self):
        data = load("lane_change")
        data["rule_engine_input"]["scenarios"] = []
        s = snapshot.from_model_result(data, "replay")["situation"]
        self.assertEqual((s["candidates"], s["default_index"]), ([], None))
        self.assertIn("과실표에서 맞는 유형을 찾지 못했습니다. 아래에서 직접 골라 주세요.", s["needs_check"])

    def test_matched_candidates_come_before_references(self):
        data = load("lane_change")
        ref = json.loads(json.dumps(data["rule_engine_input"]["scenarios"][0]))
        ref.update(accident_type=126, reference_only=True, eligible_for_adjustment=False, dashcam_table_role="A")
        data["rule_engine_input"]["scenarios"].insert(0, ref)
        cands = snapshot.from_model_result(data, "replay")["situation"]["candidates"]
        self.assertEqual([(c["accident_type_id"], c["source"]) for c in cands], [(11, "matched"), (126, "reference")])

    def test_timeline_uses_me_other_and_both(self):
        snap = snapshot.from_model_result(load("lane_change"), "replay")
        self.assertEqual({e["actor"] for e in snap["timeline"]}, {"me", "other", "both"})
        for e in snap["timeline"]:
            self.assertLessEqual(e["start_sec"], e["end_sec"])
            self.assertIn("kind", e)

    def test_flow_stage_and_relation_note_are_kept(self):
        data = load("lane_change")
        data["timeline"].append({"kind": "사고 흐름", "stage": "접근", "actor": None, "start_sec": 1.0, "end_sec": 2.0, "description": "내 차가 직진해요.",
                                 "certainty": "관찰", "evidence_text": ""})
        data["timeline_relation"] = "상대 차는 처음 보인 뒤 약 2.0초 뒤에 접촉이 의심되는 장면이 나와요."
        snap = snapshot.from_model_result(data, "replay")
        flow = [e for e in snap["timeline"] if e["kind"] == "사고 흐름"]
        self.assertEqual([(e["stage"], e["actor"]) for e in flow], [("접근", None)])
        self.assertTrue(all(e["stage"] is None for e in snap["timeline"] if e["kind"] != "사고 흐름"))
        self.assertIn("약 2.0초 뒤", snap["timeline_note"])
        self.assertIsNone(snapshot.from_model_result(load("lane_change"), "replay")["timeline_note"])   # 예전 결과에는 없다

    def test_only_video_based_facts_become_suggestions(self):
        data = load("lane_change")
        data["rule_engine_input"]["factors"] = [
            {"actor": "B", "factor": "signal_delay", "value": "있음", "status": "observed", "reason": "r"},
            {"actor": "B", "factor": "bus_lane_violation", "value": "없음", "status": "inferred"},
            {"actor": "B", "factor": "prohibited_change", "value": "있음", "status": "user"},
            {"actor": "A", "factor": "slow_failure", "value": "미확인", "status": "unknown"},
        ]
        facts = snapshot.from_model_result(data, "replay")["adjustment_facts"]
        self.assertEqual([(f["factor"], f["status"]) for f in facts], [("signal_delay", "observed"), ("bus_lane_violation", "inferred")])

    def test_snapshot_is_small_and_json_serializable(self):
        for name in ("lane_change", "parking"):
            text = json.dumps(snapshot.from_model_result(load(name), "replay"), ensure_ascii=False)
            self.assertLess(len(text), 20_000)

    def test_no_machine_specific_paths_or_filenames(self):
        text = json.dumps(snapshot.from_model_result(load("lane_change"), "replay"), ensure_ascii=False)
        for forbidden in ("/home/", ".mp4", "uploads"):
            self.assertNotIn(forbidden, text)

    def test_stage_logs(self):
        data = load("lane_change")
        data["stages"] = [{"stage": "1/3 전체 흐름 분석", "model": "gpt-4.1", "cached": False,
                           "usage": {"input_tokens": 6041, "output_tokens": 1084, "total_tokens": 7125}},
                          {"stage": "3/3 CSV 연결·과실 시나리오", "model": "gpt-4.1-mini", "cached": True, "usage": None}]
        logs = snapshot.stage_logs(data)
        self.assertEqual(logs[0], {"stage": "1/3 전체 흐름 분석", "provider": "openai", "model": "gpt-4.1", "cached": False,
                                   "input_tokens": 6041, "output_tokens": 1084})
        self.assertEqual((logs[1]["cached"], logs[1]["input_tokens"]), (True, None))


if __name__ == "__main__":
    unittest.main()
