"""블랙박스 영상 비식별화: 번호판은 검은 박스로 가리고, 사람은 전체를 블러 처리한다.

분석과 저장에는 이 함수가 만든 비식별 영상만 쓴다. 원본은 비식별이 잘못됐을 때만 다시 처리하는 용도로 세션 동안 보관한다.

기존 plate_mosaic.py(번호판만, 검은 박스)와 달리 다음이 다르다.
- 사람(보행자, 차 안 사람 포함)을 사람 전체 영역으로 블러한다. 얼굴 탐지는 블랙박스 영상에서 얼굴이 작아 놓치기 쉬워 쓰지 않았다.
- 모델을 한 번만 불러와 여러 영상에 재사용한다. (plate_mosaic.py 는 호출할 때마다 다시 불러옴)
- 탐지가 한두 프레임 빠져도 가려지도록 직전 몇 프레임의 박스를 함께 가린다 (hold_frames).
- **탐지 중 오류가 나면 영상을 만들지 않고 멈춘다.** 가리지 못한 프레임을 내보내지 않는다.
- 결과 영상을 브라우저에서 재생할 수 있게 H.264 로 다시 인코딩한다 (ffmpeg 가 있을 때).

주의: 자동 탐지는 완전하지 않다. 멀거나 어둡거나 일부만 보이는 번호판과 사람은 놓칠 수 있다.
사용자에게는 "자동으로 가리며 일부 누락될 수 있음"을 알려야 한다. 반환하는 통계(탐지 프레임 수 등)는 DB 의 video 에 기록한다.
"""
import shutil
import subprocess
from collections import deque
from pathlib import Path

import cv2

PLATE_MODEL_REPO = 'Koushim/yolov8-license-plate-detection'  # plate_mosaic.py 와 같은 번호판 모델
PERSON_WEIGHTS = 'yolov8n.pt'  # COCO 로 학습된 일반 모델. 0번 클래스가 사람(person)이다.
PERSON_CLASS_ID = 0


# ---------------------------------------------------------------- 영역 처리 (모델 없이 동작, 테스트 가능)
def expand_box(box, width, height, margin_ratio=0.1, min_margin=5):
    """탐지 박스를 여백만큼 넓히고 화면 안으로 자른다. 박스는 (x1, y1, x2, y2) 픽셀."""
    x1, y1, x2, y2 = box
    dx = max(min_margin, int((x2 - x1) * margin_ratio))
    dy = max(min_margin, int((y2 - y1) * margin_ratio))
    return (max(0, int(x1) - dx), max(0, int(y1) - dy), min(width, int(x2) + dx), min(height, int(y2) + dy))


def cover_region(frame, box):
    """영역을 검은색으로 채운다 (번호판)."""
    x1, y1, x2, y2 = box
    cv2.rectangle(frame, (x1, y1), (x2 - 1, y2 - 1), (0, 0, 0), -1)


def blur_region(frame, box, strength=0.5):
    """영역을 강하게 블러한다 (사람). 커널을 영역 크기에 비례시켜 작은 사람도, 큰 사람도 알아볼 수 없게 한다."""
    x1, y1, x2, y2 = box
    if x2 - x1 < 2 or y2 - y1 < 2:
        return
    region = frame[y1:y2, x1:x2]
    kernel = int(max(x2 - x1, y2 - y1) * strength) | 1  # 홀수
    kernel = max(15, min(kernel, 301))
    frame[y1:y2, x1:x2] = cv2.GaussianBlur(region, (kernel, kernel), 0)


# ---------------------------------------------------------------- 탐지기 (ultralytics 필요)
class YoloPlateDetector:
    """번호판 탐지. 모델은 처음 쓸 때 한 번 내려받는다."""

    def __init__(self, conf=0.25, model_path=None):
        from huggingface_hub import hf_hub_download
        from ultralytics import YOLO

        self.conf = conf
        self.model = YOLO(model_path or hf_hub_download(repo_id=PLATE_MODEL_REPO, filename='best.pt'))

    def detect(self, frame):
        boxes = self.model.predict(source=frame, conf=self.conf, verbose=False)[0].boxes.xyxy.cpu().numpy()
        return [tuple(float(v) for v in b) for b in boxes]


class YoloPersonDetector:
    """사람 탐지. 놓치는 것이 더 위험하므로 확신 기준을 낮게(0.2) 둔다."""

    def __init__(self, conf=0.2, weights=PERSON_WEIGHTS):
        from ultralytics import YOLO

        self.conf = conf
        self.model = YOLO(weights)

    def detect(self, frame):
        result = self.model.predict(source=frame, conf=self.conf, classes=[PERSON_CLASS_ID], verbose=False)[0]
        return [tuple(float(v) for v in b) for b in result.boxes.xyxy.cpu().numpy()]


# ---------------------------------------------------------------- 프레임 단위 비식별화
class Redactor:
    """프레임에서 번호판과 사람을 찾아 가린다. detect(frame) -> [(x1,y1,x2,y2), ...] 를 가진 탐지기를 받는다.

    hold_frames: 직전 N 프레임에서 찾은 박스도 함께 가린다. 탐지가 한두 프레임 빠져도 노출되지 않게 한다.
    """

    def __init__(self, plate_detector, person_detector, hold_frames=2, plate_margin=0.12, person_margin=0.1, blur_strength=0.5):
        if plate_detector is None or person_detector is None:
            raise ValueError('번호판 탐지기와 사람 탐지기가 모두 필요합니다.')
        self.plate_detector = plate_detector
        self.person_detector = person_detector
        self.plate_margin = plate_margin
        self.person_margin = person_margin
        self.blur_strength = blur_strength
        self.hold_frames = max(0, int(hold_frames))
        self.reset()

    def reset(self):
        """새 영상을 시작할 때 이전 영상의 박스를 지운다."""
        self._plates = deque(maxlen=self.hold_frames + 1)
        self._people = deque(maxlen=self.hold_frames + 1)

    def process(self, frame):
        """frame 을 제자리에서 가리고 (번호판 수, 사람 수) 를 돌려준다. 이번 프레임에서 새로 탐지한 개수이다."""
        height, width = frame.shape[:2]
        plates = [expand_box(b, width, height, self.plate_margin) for b in self.plate_detector.detect(frame)]
        people = [expand_box(b, width, height, self.person_margin, min_margin=8) for b in self.person_detector.detect(frame)]
        self._plates.append(plates)
        self._people.append(people)
        # 사람 블러를 먼저 하고, 번호판 검은 박스를 나중에 덮는다 (번호판이 사람 영역 안에 있어도 검게 남도록)
        for boxes in self._people:
            for box in boxes:
                blur_region(frame, box, self.blur_strength)
        for boxes in self._plates:
            for box in boxes:
                cover_region(frame, box)
        return len(plates), len(people)


_default = None


def default_redactor():
    """서버에서 쓰는 공용 Redactor. 모델은 처음 호출할 때 한 번만 불러온다. (동시에 여러 영상을 처리하려면 영상마다 새로 만들 것)"""
    global _default
    if _default is None:
        _default = Redactor(YoloPlateDetector(), YoloPersonDetector())
    return _default


# ---------------------------------------------------------------- 영상 처리
def _reencode_h264(src, dst):
    """브라우저에서 재생되는 H.264 로 다시 인코딩한다. ffmpeg 가 없거나 실패하면 False."""
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg is None:
        return False
    result = subprocess.run(
        [ffmpeg, '-y', '-i', str(src), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', str(dst)],
        capture_output=True,
    )
    return result.returncode == 0 and Path(dst).is_file() and Path(dst).stat().st_size > 0


def redact_video(input_path, output_path, redactor=None, reencode=True):
    """영상의 번호판과 사람을 가려 output_path 에 저장하고 통계를 돌려준다.

    반환: {'output_path', 'frames', 'frames_with_plates', 'plate_detections', 'frames_with_people',
          'person_detections', 'fps', 'width', 'height', 'duration', 'reencoded'}
    reencoded 가 False 이면 mp4v 로 저장된 것이라 브라우저에서 재생되지 않을 수 있다 (ffmpeg 설치 필요).
    소리는 포함하지 않는다.
    오류가 나면 만들던 파일을 지우고 예외를 그대로 올린다. 가리지 못한 영상은 남기지 않는다.
    """
    input_path, output_path = Path(input_path), Path(output_path)
    if not input_path.is_file():
        raise FileNotFoundError(f'입력 영상이 없습니다: {input_path}')
    if input_path.resolve() == output_path.resolve():
        raise ValueError('입력과 출력 경로가 같으면 안 됩니다.')
    redactor = redactor or default_redactor()
    redactor.reset()

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise ValueError(f'영상을 열 수 없습니다: {input_path}')
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if fps <= 0 or width <= 0 or height <= 0:
        cap.release()
        raise ValueError('영상 정보를 읽을 수 없습니다.')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path = output_path.with_name(output_path.stem + '.raw.mp4')
    writer = cv2.VideoWriter(str(raw_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise ValueError(f'영상을 저장할 수 없습니다: {raw_path}')

    frames = frames_with_plates = plate_detections = frames_with_people = person_detections = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            plates, people = redactor.process(frame)
            frames_with_plates += bool(plates)
            frames_with_people += bool(people)
            plate_detections += plates
            person_detections += people
            writer.write(frame)
            frames += 1
        cap.release()
        writer.release()
        if frames == 0:
            raise ValueError('읽을 수 있는 프레임이 없습니다.')
        reencoded = reencode and _reencode_h264(raw_path, output_path)
        if not reencoded:
            shutil.move(str(raw_path), str(output_path))
    except BaseException:
        cap.release()
        writer.release()
        output_path.unlink(missing_ok=True)
        raise
    finally:
        raw_path.unlink(missing_ok=True)

    return {
        'output_path': str(output_path), 'frames': frames,
        'frames_with_plates': frames_with_plates, 'plate_detections': plate_detections,
        'frames_with_people': frames_with_people, 'person_detections': person_detections,
        'fps': fps, 'width': width, 'height': height, 'duration': frames / fps, 'reencoded': bool(reencoded),
    }


if __name__ == '__main__':
    import argparse
    import json

    parser = argparse.ArgumentParser(description='영상의 번호판(검은 박스)과 사람(블러)을 가립니다')
    parser.add_argument('input', help='입력 영상 경로')
    parser.add_argument('output', help='출력 영상 경로')
    args = parser.parse_args()
    print(json.dumps(redact_video(args.input, args.output), ensure_ascii=False, indent=1))
