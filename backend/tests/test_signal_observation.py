"""신호 관찰(B 단계): 프롬프트가 파이프라인에 들어가 있고, 근거 없는 신호 값은 후보 선택에 쓰이지 않는다."""

import json
import re
import unittest
from pathlib import Path

MODEL = Path(__file__).resolve().parents[1] / "model" / "avly"
FIXTURES = Path(__file__).parent / "fixtures"

try:
    import pydantic  # noqa: F401
    HAVE_RUNTIME = True
except ImportError:   # 이 PC 처럼 서버 의존성이 없는 곳에서는 프롬프트 검사만 한다
    HAVE_RUNTIME = False


class PromptTests(unittest.TestCase):
    def test_pipeline_appends_every_detail_review_rule_file_that_exists(self):
        pipeline = (MODEL / "pipeline.py").read_text(encoding="utf-8")
        files = sorted(p.stem for p in (MODEL / "prompts").glob("detail_review_rule_*.txt"))
        used = set(re.findall(r"prompt_text\('(detail_review_rule_\d+)'\)", pipeline))
        self.assertEqual(set(files), used, "프롬프트 파일을 만들고 파이프라인에 넣지 않은 규칙이 있다")

    def test_signal_and_impact_place_rules_are_in_the_prompt(self):
        text = (MODEL / "prompts" / "detail_review_rule_12.txt").read_text(encoding="utf-8")
        for needle in ("signal_present", "signal_operating", "a_signal", "b_signal", "evidence_frame_ids", "impact_anchor_frame_id", "road_place_codes"):
            self.assertIn(needle, text)
        # 신호등이 안 보인다는 이유로 '없음'을 쓰지 못하게 하고, 상대 차 신호를 추정하지 못하게 한다
        self.assertIn("보이지 않는다는 이유만으로 없음", text)
        self.assertIn("거꾸로 추정하지 마라", text)

    def test_prompt_never_asks_for_fault_judgement(self):
        text = (MODEL / "prompts" / "detail_review_rule_12.txt").read_text(encoding="utf-8")
        for word in ("과실", "책임", "위반", "가해", "피해"):
            self.assertNotIn(word, text)

    def test_rule_file_is_separated_from_the_previous_prompt(self):
        self.assertTrue((MODEL / "prompts" / "detail_review_rule_12.txt").read_text(encoding="utf-8").startswith("\n"))


@unittest.skipUnless(HAVE_RUNTIME, "pydantic 이 없어 건너뜁니다 (worker 컨테이너에서 실행)")
class SanitizeTests(unittest.TestCase):
    def scene(self, **signal):
        import sys
        sys.path.insert(0, str(MODEL.parent))
        from avly.schemas import Observation, SignalCheck
        data = json.loads((FIXTURES / "model_result_lane_change.json").read_text(encoding="utf-8"))
        scene = Observation.model_validate({"tracks": [], "b_screen_points": [], **data["scene"]})   # 시험용 파일에는 이 두 항목이 빠져 있다
        scene.signal_check = SignalCheck(**signal)
        return scene

    def sanitize(self, scene):
        import sys
        sys.path.insert(0, str(MODEL.parent))
        from avly.observation import sanitize_signal_check
        return sanitize_signal_check(scene)

    def test_signal_values_without_two_frames_are_reset_to_unknown(self):
        scene = self.scene(signal_present="있음", signal_operating="정상 작동", a_signal="녹색", evidence_frame_ids=["frame_000001"])
        self.assertTrue(self.sanitize(scene))
        sig = scene.signal_check
        self.assertEqual((sig.signal_present, sig.signal_operating, sig.a_signal, sig.b_signal), ("미확인",) * 4)
        self.assertTrue(any("신호 관찰의 근거 프레임이 2장 미만" in x for x in scene.observation_issues))

    def test_signal_values_with_two_distinct_frames_are_kept(self):
        scene = self.scene(signal_present="있음", signal_operating="정상 작동", a_signal="적색", evidence_frame_ids=["frame_000001", "frame_000002"])
        self.assertFalse(self.sanitize(scene))
        self.assertEqual(scene.signal_check.a_signal, "적색")

    def test_the_same_frame_twice_is_not_two_frames(self):
        scene = self.scene(signal_present="있음", evidence_frame_ids=["frame_000001", "frame_000001"])
        self.assertTrue(self.sanitize(scene))

    def test_all_unknown_is_left_alone_without_a_note(self):
        scene = self.scene()
        before = list(scene.observation_issues)
        self.assertFalse(self.sanitize(scene))
        self.assertEqual(scene.observation_issues, before)

    def test_a_guessed_no_signal_does_not_survive_either(self):
        # 신호등이 안 보여서 '없음'이라고만 쓴 경우도 근거 2장이 없으면 쓰지 않는다
        scene = self.scene(signal_present="없음", evidence_frame_ids=["frame_000009"])
        self.assertTrue(self.sanitize(scene))
        self.assertEqual(scene.signal_check.signal_present, "미확인")


if __name__ == "__main__":
    unittest.main()
