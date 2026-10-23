"""데이터·프롬프트 파일 읽기와 환경변수 설정.

- data/*.json     : 표 데이터 (가감요소, 판례, 법조문, 라벨, 설문 선택지)
- prompts/*.txt   : AI 에게 보내는 프롬프트 문장
- dev/            : 개발용 설정 (기본은 꺼져 있음)
"""
import json
import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / 'data'
PROMPT_DIR = PACKAGE_DIR / 'prompts'


def load_json(name):
    with open(DATA_DIR / name, encoding='utf-8') as f:
        return json.load(f)


def prompt_text(name):
    # newline='' : 줄바꿈 문자를 바꾸지 않고 파일 내용 그대로 읽는다 (프롬프트 앞뒤 공백/줄바꿈도 의미가 있다)
    with open(PROMPT_DIR / (name + '.txt'), encoding='utf-8', newline='') as f:
        return f.read()


def setting(name, default):
    """환경변수 name 이 있으면 default 와 같은 타입으로 바꿔서 쓰고, 없으면 default 를 쓴다."""
    value = os.environ.get(name)
    return default if value is None else type(default)(value)


def dev_overrides():
    """AVLY_DEV_OVERRIDES 가 가리키는 JSON 에서 (영상별 확인값, 도로 확인값)을 읽는다. 없으면 둘 다 빈 dict."""
    path = os.environ.get('AVLY_DEV_OVERRIDES')
    if not path:
        return {}, {}
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return data.get('video', {}), data.get('road', {})
