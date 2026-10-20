"""사고 흐름(accident_flow): AI 가 쓴 단계를 정리하고 타임라인으로 만든다. AI 를 부르지 않고 가짜 관찰 결과로 시험한다."""

import unittest
from types import SimpleNamespace as NS

from avly.observation import clean_accident_flow
from avly.schemas import FlowStep
from avly.timeline import build_timeline, relation_note

FRAMES = [{"id": f"frame_{i:06d}", "index": i, "sec": i / 30} for i in (0, 30, 60, 90, 120, 150, 180)]   # 0, 1, 2 ... 6초
F = {i: f"frame_{i:06d}" for i in (0, 30, 60, 90, 120, 150, 180)}


def step(stage, first, last, text="내 차가 직진하고 있어요.", support="관찰"):
    return FlowStep(stage=stage, description=text, support=support, first_frame_id=F[first], last_frame_id=F[last], evidence_frame_ids=[F[first], F[last]])


def scene(steps, contact="접촉 추정"):
    return NS(accident_flow=steps, contact=contact, observation_issues=[])


class CleanTests(unittest.TestCase):
    def test_valid_steps_are_kept_in_time_order(self):
        s = scene([step("접촉", 90, 120, "접촉이 의심되는 장면이에요."), step("접근", 0, 60), step("사고 직전", 60, 90, "상대 차가 오른쪽에서 가까워져요.")])
        self.assertEqual(clean_accident_flow(s, FRAMES), 3)
        self.assertEqual([x.stage for x in s.accident_flow], ["접근", "사고 직전", "접촉"])
        self.assertEqual(s.observation_issues, [])

    def test_bad_steps_are_dropped_without_failing_the_analysis(self):
        s = scene([
            step("접근", 0, 60),
            step("접근", 60, 90),                                       # 같은 단계 반복
            step("사고 직전", 120, 90, "거꾸로인 구간이에요."),             # 시작이 끝보다 늦다
            step("접촉", 90, 120, "상대 차의 과실이 커 보여요."),          # 판단 표현
            step("접촉 이후", 120, 150, "약 3초 뒤에 멈췄어요."),          # 수치
        ])
        self.assertEqual(clean_accident_flow(s, FRAMES), 1)
        self.assertEqual(len(s.observation_issues), 4)
        self.assertTrue(all(i.startswith("사고 흐름") for i in s.observation_issues))

    def test_contact_is_not_claimed_unless_it_was_observed(self):
        claim = step("접촉", 90, 120, "두 차가 부딪혔어요.")
        unsure = scene([claim], contact="접촉 추정")
        self.assertEqual(clean_accident_flow(unsure, FRAMES), 0)
        self.assertIn("접촉을 단정", unsure.observation_issues[0])
        seen = scene([step("접촉", 90, 120, "두 차가 부딪혔어요.")], contact="접촉 관찰")
        self.assertEqual(clean_accident_flow(seen, FRAMES), 1)

    def test_at_most_four_steps(self):
        s = scene([step("접근", 0, 30), step("사고 직전", 30, 60), step("접촉", 60, 90, "접촉이 의심돼요."), step("접촉 이후", 90, 120)])
        self.assertEqual(clean_accident_flow(s, FRAMES), 4)

    def test_unknown_frames_are_dropped(self):
        bad = FlowStep(stage="접근", description="내 차가 직진해요.", support="관찰", first_frame_id="frame_999999", last_frame_id=F[60], evidence_frame_ids=[])
        self.assertEqual(clean_accident_flow(scene([bad]), FRAMES), 0)


def model_scene(**extra):
    base = {"a_phases": [], "tracks": [{"vehicle_id": "V1", "first_frame_id": F[30], "last_frame_id": F[150]}], "b_vehicle_id": "V1", "b_identity": "구별됨",
            "contact": "접촉 추정", "contact_frame_ids": [F[90], F[120]], "b_screen_points": [{"frame_id": F[30], "x_center": 0.9, "visibility": "차량 중심 식별 가능"}],
            "accident_flow": [], "impact_anchor_frame_id": None}
    return {**base, **extra}


class TimelineTests(unittest.TestCase):
    def test_flow_steps_become_timeline_events_with_their_stage(self):
        flow = [{"stage": "접근", "description": "내 차가 직진해요.", "support": "관찰", "first_frame_id": F[0], "last_frame_id": F[60], "evidence_frame_ids": [F[30], F[0]]},
                {"stage": "접촉", "description": "접촉이 의심돼요.", "support": "추정", "first_frame_id": F[90], "last_frame_id": F[120], "evidence_frame_ids": [F[90]]}]
        payload = build_timeline(model_scene(accident_flow=flow), FRAMES)
        events = [e for e in payload["timeline"] if e["kind"] == "사고 흐름"]
        self.assertEqual([(e["stage"], round(e["start_sec"], 1), round(e["end_sec"], 1), e["certainty"]) for e in events], [("접근", 0.0, 2.0, "관찰"), ("접촉", 3.0, 4.0, "추정")])
        self.assertEqual(events[0]["evidence_frame_ids"], [F[0], F[30]])   # 시간순으로 정리된다
        self.assertTrue({"B 확인 구간", "접촉 근거 구간"} <= {e["kind"] for e in payload["timeline"]})   # 기존 근거 구간도 남는다

    def test_a_scene_without_flow_builds_the_same_timeline_as_before(self):
        payload = build_timeline(model_scene(), FRAMES)
        self.assertFalse([e for e in payload["timeline"] if e["kind"] == "사고 흐름"])

    def test_relation_sentence_uses_only_video_time_and_the_side_it_appeared_from(self):
        note = build_timeline(model_scene(), FRAMES)["timeline_relation"]
        self.assertIn("화면 오른쪽", note)
        self.assertIn("약 2.0초 뒤", note)                         # 상대 차 첫 장면 1초 → 접촉 근거 첫 장면 3초
        self.assertIn("접촉이 의심되는 장면", note)
        self.assertIn("속도나 거리, 피할 수 있었는지는 영상만으로 알 수 없어요", note)
        self.assertNotRegex(note, r"km|m/s|과실")

    def test_relation_sentence_is_left_out_when_the_other_car_or_contact_is_unclear(self):
        times = {i["id"]: i["sec"] for i in FRAMES}
        self.assertIsNone(relation_note(model_scene(b_identity="혼동 가능"), times))
        self.assertIsNone(relation_note(model_scene(contact="판단 불가"), times))
        self.assertIsNone(relation_note(model_scene(contact_frame_ids=[]), times))
        self.assertIsNone(relation_note(model_scene(contact_frame_ids=[F[30]]), times))   # 처음 보인 장면과 같은 시각이면 의미 없다
        self.assertNotIn("화면", relation_note(model_scene(b_screen_points=[]), times))      # 방향을 모르면 방향은 말하지 않는다

    def test_side_is_chosen_from_the_first_visible_position(self):
        times = {i["id"]: i["sec"] for i in FRAMES}
        for x, word in ((0.1, "왼쪽"), (0.5, "가운데"), (0.9, "오른쪽")):
            points = [{"frame_id": F[30], "x_center": x, "visibility": "차량 중심 식별 가능"}, {"frame_id": F[60], "x_center": 0.5, "visibility": "차량 중심 식별 가능"}]
            self.assertIn(f"화면 {word}쪽", relation_note(model_scene(b_screen_points=points), times))


if __name__ == "__main__":
    unittest.main()
