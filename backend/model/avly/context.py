"""실행 중 여러 함수가 함께 읽고 쓰는 상태.

원래 Avly.py 에서는 모듈 전역 변수였다. 파일을 나누면서 ctx 객체의 속성으로 옮겼다.
주의: 지금은 프로세스에 하나뿐인 객체라서 분석을 동시에 두 개 실행할 수 없다(원래와 동일한 제약).
"""


class Context:
    # 영상/CSV 읽기 결과
    table = None
    places = None
    csv_hash = None
    csv_path = None
    csv_normalization = None
    video_hash = None
    VIDEO_PATH = None
    fps = None
    frame_count = None
    last_frame_index = None
    duration = None
    video_read_audit = None
    cap = None
    # 결과 저장 위치
    result_dir = None
    cache_dir = None
    output_path = None
    # 호출 집계
    client = None
    meter = None
    stages = None
    # 실행 옵션
    USE_CACHE = True
    SHOW_FRAMES = False
    SHOW_PROCESS_LOGS = False


ctx = Context()
