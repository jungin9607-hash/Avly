"""실제 탐지 모델이 이 PC 에서 동작하는지 확인하는 스크립트. (단위 테스트가 아니다: 모델을 내려받고 인터넷에서 예제 사진을 받는다)

  cd backend && python -m plate.check_models [사진 경로]

사진을 주지 않으면 ultralytics 문서의 예제 사진(사람 4명과 버스)을 내려받아 쓴다.
확인하는 것: 사람 탐지, 번호판 탐지, 사람 영역이 실제로 흐려지는지, 한 프레임당 처리 시간.
번호판이 안 잡히는 것은 사진에 번호판이 없을 수 있어서 오류가 아니다. 번호판이 보이는 차량 사진을 직접 넣어 확인하라.
"""
import sys
import time
import urllib.request

import cv2

from plate import redact

SAMPLE_URL = "https://ultralytics.com/images/bus.jpg"


def sharpness(image, box):
    x1, y1, x2, y2 = (int(v) for v in box)
    return float(cv2.cvtColor(image[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY).std())


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/avly_sample.jpg"
    if len(sys.argv) <= 1:
        urllib.request.urlretrieve(SAMPLE_URL, path)
    frame = cv2.imread(path)
    if frame is None:
        raise SystemExit(f"사진을 읽을 수 없습니다: {path}")
    print("사진", path, frame.shape[:2])

    started = time.time()
    person, plate = redact.YoloPersonDetector(), redact.YoloPlateDetector()
    print(f"모델 불러오기 {time.time() - started:.1f}초 (처음에는 모델을 내려받는다)")
    people, plates = person.detect(frame), plate.detect(frame)   # 첫 호출은 워밍업이라 느리다
    print("사람", len(people), "명, 번호판", len(plates), "개")

    big = cv2.resize(frame, (1920, 1080))
    count = 15
    started = time.time()
    for _ in range(count):
        person.detect(big)
        plate.detect(big)
    per_frame = (time.time() - started) / count
    print(f"1920x1080 한 프레임 처리 {per_frame:.3f}초 → 15초 영상(30fps, 450프레임) 약 {450 * per_frame:.0f}초 (탐지만, 영상 읽기·쓰기·변환 제외)")

    before = frame.copy()
    redact.Redactor(plate, person, hold_frames=0).process(frame)
    for box in people:
        print(f"  사람 영역 선명도(표준편차) {sharpness(before, box):.1f} → {sharpness(frame, box):.1f}")
    out = path.rsplit(".", 1)[0] + "_redacted.jpg"
    cv2.imwrite(out, frame)
    print("가린 결과 사진:", out, "(눈으로 확인하세요)")


if __name__ == "__main__":
    main()
