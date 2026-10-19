"""표 형태 데이터. 값은 data/*.json 에 있고, 여기서는 읽어서 예전과 같은 이름의 변수로 내놓는다.

값을 고치려면 data/ 의 JSON 파일을 수정한다. (코드는 건드리지 않는다)
JSON 은 키를 문자열로만 저장하므로 숫자 키(유형 번호)와 튜플은 읽을 때 되돌린다.
"""
from .dataio import dev_overrides, load_json

SUPPORT_LABELS = load_json('support_labels.json')

SPECIAL_LABELS = load_json('special_labels.json')

FACTOR_LABELS = load_json('factor_labels.json')

ADJUSTMENT_RULES = load_json('adjustment_rules.json')

LAW_ARTICLES_BY_TYPE = {int(k): v for k, v in load_json('law_articles.json').items()}

VERIFIED_CASES = {int(k): v for k, v in load_json('verified_cases.json').items()}

SURVEY_CONTEXT_OPTIONS = load_json('survey_options.json')

CAUSE_QUESTIONS = {k: [tuple(q) for q in v] for k, v in load_json('cause_questions.json').items()}

CAUSE_KEYS = {k for specs in CAUSE_QUESTIONS.values() for k, _, _ in specs}

# 특정 영상 강제 덮어쓰기: 기본은 꺼져 있다 (dev/confirmed_contexts.json 참고)
CONFIRMED_VIDEO_CONTEXT, CONFIRMED_ROAD_CONTEXT = dev_overrides()
