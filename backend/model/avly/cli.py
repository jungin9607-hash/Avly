"""터미널 실행 진입점.

backend/model 폴더에서:  python -m avly.cli --video "uploads/영상.mp4"
(원래는 backend 폴더에서 python model/Avly.py --video ... 로 실행했다.)
"""
import argparse

from .pipeline import run


def parse_args():
    parser = argparse.ArgumentParser(description='에블리: 영상 분석 → 터미널 설문 → 참고 보고서')
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument('--video', help='영상 경로. 생략하면 영상 선택 메뉴 표시')
    selector.add_argument('--pick-video', action='store_true', help='파일 선택 창. GUI 미지원 시 터미널 메뉴')
    parser.add_argument('--backend', help='backend 폴더의 절대 경로. 기본값: 자동 탐색')
    parser.add_argument('--csv', help='fault_table.csv 경로. 기본값: model/data 등 자동 탐색')
    parser.add_argument('--results', help='결과 폴더 경로. 기본값: model/results')
    parser.add_argument('--show-logs', action='store_true', help='단계별 처리 로그 표시')
    parser.add_argument('--no-cache', action='store_true', help='저장된 Vision 응답 대신 새 API 요청')
    parser.add_argument('--no-survey', action='store_true', help='설문 없이 영상 분석 보고서만 저장·표시')
    return parser.parse_args()


def main():
    args = parse_args()
    run({
        'BACKEND_DIR': args.backend,
        'VIDEO_FILE': args.video,
        'PICK_VIDEO': args.pick_video,
        'CSV_FILE': args.csv,
        'RESULTS_DIR': args.results,
        'SHOW_PROCESS_LOGS': args.show_logs,
        'USE_CACHE': not args.no_cache,
        'no_survey': args.no_survey,
    })


if __name__ == '__main__':
    main()
