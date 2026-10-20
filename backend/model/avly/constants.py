"""단일 값 상수와 프롬프트 문구. (2단계에서 prompts/ 와 JSON 으로 분리할 대상)"""
from .dataio import prompt_text, setting
from typing import Literal


VERSION = 'auto-three-stage-v2.21.0-identity-and-survey-recovery'

CODE_VERSION = 'auto-three-stage-v2.21.2-accident-flow'

VISION_MODEL = setting('AVLY_VISION_MODEL', 'gpt-4.1')

MATCH_MODEL = setting('AVLY_MATCH_MODEL', 'gpt-4.1-mini')

COMPARE_MODEL = setting('AVLY_COMPARE_MODEL', 'gpt-4.1-mini')   # 판례와 내 사고 비교 (텍스트만 보낸다)

STEP_SECONDS = setting('AVLY_STEP_SECONDS', 1 / 3)

OVERVIEW_MAX_IMAGES = setting('AVLY_OVERVIEW_MAX_IMAGES', 80)

REVIEW_IMAGES = setting('AVLY_REVIEW_IMAGES', 40)

REVIEW_HIGH_IMAGES = setting('AVLY_REVIEW_HIGH_IMAGES', 8)

PRE_SECONDS = setting('AVLY_PRE_SECONDS', 4.0)

POST_SECONDS = setting('AVLY_POST_SECONDS', 2.0)

CATALOG_LIMIT = None

ACCIDENT_CONFIRMED_INPUT = True

VERBOSE = False

Action = Literal['정지/대기', '주차 중', '후진', '주차 출차', '출발', '직진', '교차로 진입', '교차로 내 회전', '진출', '좌회전', '우회전', '진로변경', '기타', '미확인']

ROLE = prompt_text('role')

ACCURACY_RULES = prompt_text('accuracy_rules')

TIMELINE_NOTICE = '시간은 프레임 이미지에 표시한 값과 같습니다. 구간은 분석 근거가 기록된 시점의 범위이며, 그동안 계속 접촉했다거나 정확한 충돌 순간이라는 뜻은 아닙니다.'

DETAIL_GATE_VERSION = 'contact-evidence-gate-v1'

RULE_ENGINE_VERSION = 'avly-adjustments-v1.1'

RULE_SOURCE = 'https://accident.knia.or.kr/myaccident-content?chartNo=%EC%B0%A843-2&chartType=1'

RULE_ENGINE_VERSION = 'avly-adjustments-v1.2-json-parking'

LAW_API_ENABLED = True

LAW_SECRET_NAME = 'law_api'

LAW_ACCIDENT_DATE = None

CASE_TARGET_COUNT = 3

CASE_API_ENABLED = True

CASE_MAX_BODY_REQUESTS = 20

CASE_RELEVANCE_VERSION = 'v2205-civil-claim-context'

REPORT_NOTICE = '※ 본 보고서는 법적 효력이 없는 AI 참고 자료입니다. 실제 과실비율이나 법적 책임을 확정하지 않습니다.'

# 서비스가 지원하는 사고 대상 (과실표 fault_table_car_to_car.csv 의 accident_object_name)
SUPPORTED_ACCIDENT_OBJECTS = ('차대차',)

# 영상 길이 상한(초). 사고 전후 15초 내외 영상을 기준으로 하고 여유를 두어 20초까지 받는다.
MAX_VIDEO_SECONDS = setting('AVLY_MAX_VIDEO_SECONDS', 20.0)
