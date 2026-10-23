"""redact.py 테스트. 실제 모델(ultralytics)은 쓰지 않고, 정해 둔 박스를 돌려주는 가짜 탐지기를 쓴다.

실행 (backend 폴더에서):  python -m unittest plate.test_redact -v
필요한 패키지: numpy, opencv-python-headless
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cv2
import numpy as np

from plate import redact
from plate.redact import Redactor, blur_region, cover_region, expand_box, redact_video

W, H = 160, 120


class ScriptedDetector:
    """detect 를 부를 때마다 다음 프레임의 박스를 돌려준다. script: {프레임 번호: [박스, ...]}"""

    def __init__(self, script, fail_at=None):
        self.script = script
        self.fail_at = fail_at
        self.calls = 0

    def detect(self, frame):
        index = self.calls
        self.calls += 1
        if index == self.fail_at:
            raise RuntimeError('탐지 실패')
        return list(self.script.get(index, []))


def noise_frame(seed=0):
    return np.random.default_rng(seed).integers(0, 256, (H, W, 3), dtype=np.uint8)


def spread(frame, box):
    x1, y1, x2, y2 = box
    return float(np.std(cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)))


def make_video(path, frames=12, fps=10):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (W, H))
    for i in range(frames):
        writer.write(noise_frame(i))
    writer.release()


class RegionTests(unittest.TestCase):
    def test_expand_box_adds_margin_and_clamps_to_frame(self):
        self.assertEqual(expand_box((50, 40, 90, 80), W, H, margin_ratio=0.1, min_margin=5), (45, 35, 95, 85))
        self.assertEqual(expand_box((0, 0, 10, 10), W, H, margin_ratio=0.1, min_margin=5), (0, 0, 15, 15))
        self.assertEqual(expand_box((150, 110, 160, 120), W, H, margin_ratio=0.5, min_margin=5), (145, 105, 160, 120))

    def test_cover_region_is_black_and_leaves_outside_untouched(self):
        frame = noise_frame(1)
        before = frame.copy()
        cover_region(frame, (20, 20, 60, 50))
        self.assertEqual(int(frame[20:50, 20:60].max()), 0)
        self.assertTrue(np.array_equal(frame[:, 70:], before[:, 70:]))
        self.assertTrue(np.array_equal(frame[60:, :], before[60:, :]))

    def test_blur_region_smooths_inside_and_leaves_outside_untouched(self):
        frame = noise_frame(2)
        before = frame.copy()
        box = (40, 20, 100, 100)
        blur_region(frame, box)
        self.assertLess(spread(frame, box), spread(before, box) * 0.3)
        self.assertTrue(np.array_equal(frame[:, :40], before[:, :40]))
        self.assertTrue(np.array_equal(frame[:, 100:], before[:, 100:]))
        self.assertTrue(np.array_equal(frame[:20], before[:20]))

    def test_blur_region_ignores_degenerate_box(self):
        frame = noise_frame(3)
        before = frame.copy()
        blur_region(frame, (10, 10, 10, 50))
        self.assertTrue(np.array_equal(frame, before))


class RedactorTests(unittest.TestCase):
    def test_plate_is_black_and_person_is_blurred(self):
        plate, person = (20, 20, 50, 40), (80, 30, 140, 110)
        redactor = Redactor(ScriptedDetector({0: [plate]}), ScriptedDetector({0: [person]}), hold_frames=0)
        frame = noise_frame(4)
        before = frame.copy()
        counts = redactor.process(frame)
        self.assertEqual(counts, (1, 1))
        px = expand_box(plate, W, H, 0.12)
        self.assertEqual(int(frame[px[1]:px[3], px[0]:px[2]].max()), 0)
        self.assertLess(spread(frame, person), spread(before, person) * 0.3)

    def test_plate_stays_black_when_inside_a_person(self):
        person, plate = (40, 20, 120, 110), (60, 50, 90, 65)
        redactor = Redactor(ScriptedDetector({0: [plate]}), ScriptedDetector({0: [person]}), hold_frames=0)
        frame = noise_frame(5)
        redactor.process(frame)
        self.assertEqual(int(frame[52:63, 62:88].max()), 0)

    def test_missed_detection_is_covered_by_hold_frames(self):
        person = (40, 20, 110, 100)
        # 프레임 0 에서만 탐지되고 이후는 놓친 경우
        redactor = Redactor(ScriptedDetector({}), ScriptedDetector({0: [person]}), hold_frames=2)
        results = []
        for i in range(5):
            frame = noise_frame(10 + i)
            before = frame.copy()
            redactor.process(frame)
            results.append(spread(frame, person) < spread(before, person) * 0.3)
        # 프레임 0, 1, 2 는 가려지고, 3 부터는 풀린다
        self.assertEqual(results, [True, True, True, False, False])

    def test_reset_clears_held_boxes_between_videos(self):
        person = (40, 20, 110, 100)
        redactor = Redactor(ScriptedDetector({0: [person]}), ScriptedDetector({0: [person]}), hold_frames=3)
        redactor.process(noise_frame(20))
        redactor.reset()
        frame = noise_frame(21)
        before = frame.copy()
        redactor.process(frame)  # 탐지기 대본에는 0번 프레임만 있으므로 이번엔 탐지 없음
        self.assertTrue(np.array_equal(frame, before))

    def test_requires_both_detectors(self):
        with self.assertRaises(ValueError):
            Redactor(None, ScriptedDetector({}))
        with self.assertRaises(ValueError):
            Redactor(ScriptedDetector({}), None)


class VideoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.src = self.dir / 'in.mp4'
        make_video(self.src)

    def tearDown(self):
        self.tmp.cleanup()

    def scripted(self, **kw):
        person = (40, 20, 110, 100)
        plate = (10, 10, 40, 25)
        return Redactor(ScriptedDetector({i: [plate] for i in range(0, 12, 2)}, kw.get('plate_fail')),
                        ScriptedDetector({i: [person] for i in range(3, 9)}, kw.get('person_fail')), hold_frames=1)

    def test_redacts_every_frame_and_reports_stats(self):
        out = self.dir / 'out.mp4'
        with mock.patch.object(redact.shutil, 'which', return_value=None):  # ffmpeg 없는 환경도 확인
            stats = redact_video(self.src, out, redactor=self.scripted())
        self.assertTrue(out.is_file())
        self.assertEqual(stats['frames'], 12)
        self.assertEqual((stats['width'], stats['height']), (W, H))
        self.assertEqual(stats['frames_with_plates'], 6)
        self.assertEqual(stats['plate_detections'], 6)
        self.assertEqual(stats['frames_with_people'], 6)
        self.assertEqual(stats['person_detections'], 6)
        self.assertFalse(stats['reencoded'])
        self.assertAlmostEqual(stats['duration'], 1.2, places=3)
        # 만든 영상을 다시 읽어서 사람 영역이 실제로 흐려졌는지 확인 (코덱 손실이 있으니 비율로 비교)
        cap = cv2.VideoCapture(str(out))
        frames = []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(frame)
        cap.release()
        self.assertEqual(len(frames), 12)
        person = (40, 20, 110, 100)
        self.assertLess(spread(frames[5], person), spread(frames[0], person) * 0.5)
        self.assertLess(float(frames[0][12:22, 12:38].mean()), 12)  # 번호판 자리는 검다

    def test_no_temp_file_left_behind(self):
        out = self.dir / 'out.mp4'
        redact_video(self.src, out, redactor=self.scripted())
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ['in.mp4', 'out.mp4'])

    def test_detector_error_leaves_no_output(self):
        out = self.dir / 'out.mp4'
        with self.assertRaises(RuntimeError):
            redact_video(self.src, out, redactor=self.scripted(person_fail=6))
        self.assertFalse(out.exists())
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ['in.mp4'])

    def test_reencode_failure_falls_back_to_raw_video(self):
        out = self.dir / 'out.mp4'
        with mock.patch.object(redact, '_reencode_h264', return_value=False):
            stats = redact_video(self.src, out, redactor=self.scripted())
        self.assertTrue(out.is_file())
        self.assertFalse(stats['reencoded'])

    def test_rejects_bad_paths(self):
        with self.assertRaises(FileNotFoundError):
            redact_video(self.dir / 'none.mp4', self.dir / 'o.mp4', redactor=self.scripted())
        with self.assertRaises(ValueError):
            redact_video(self.src, self.src, redactor=self.scripted())

    def test_unreadable_video_is_rejected(self):
        bad = self.dir / 'bad.mp4'
        bad.write_bytes(b'not a video')
        with self.assertRaises(ValueError):
            redact_video(bad, self.dir / 'o.mp4', redactor=self.scripted())
        self.assertFalse((self.dir / 'o.mp4').exists())


if __name__ == '__main__':
    unittest.main()
