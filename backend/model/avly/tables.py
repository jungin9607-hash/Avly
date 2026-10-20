"""표 형태 데이터. 값은 data/*.json 에 있고, 여기서는 읽어서 예전과 같은 이름의 변수로 내놓는다.

값을 고치려면 data/ 의 JSON 파일을 수정한다. (코드는 건드리지 않는다)
JSON 은 키를 문자열로만 저장하므로 숫자 키(유형 번호)와 튜플은 읽을 때 되돌린다.
"""
from .dataio import dev_overrides, load_json, setting

SUPPORT_LABELS = load_json('support_labels.json')

SPECIAL_LABELS = load_json('special_labels.json')

FACTOR_LABELS = load_json('factor_labels.json')



def type_is_reviewed(config):
    """유형의 가감요소를 사람이 확인했는지. 유형에 reviewed: true 가 있거나, 규칙마다 reviewed: true 이면 확인한 것이다.
    reviewed 항목이 아예 없는 유형(사람이 먼저 입력해 둔 기존 7개)은 확인한 것으로 본다."""
    if 'reviewed' not in config and not any('reviewed' in r for r in config['rules']):
        return True
    return bool(config.get('reviewed')) or (bool(config['rules']) and all(r.get('reviewed') for r in config['rules']))


def active_rules(all_rules, require_review):
    """계산과 질문에 쓰는 가감요소 규칙. require_review 이면 사람이 확인한 유형만 쓰고 나머지는 '미등록'(기본 비율만 안내)이 된다."""
    return {k: v for k, v in all_rules.items() if not require_review or type_is_reviewed(v)}


ALL_ADJUSTMENT_RULES = load_json('adjustment_rules.json')   # 확인 여부와 상관없이 파일에 있는 전부 (검수 도구가 쓴다)

# 기본은 확인한 유형만 켠다. 개발·시험에서 전부 보려면 환경변수 AVLY_REQUIRE_RULE_REVIEW=0
REQUIRE_RULE_REVIEW = bool(setting('AVLY_REQUIRE_RULE_REVIEW', 1))

ADJUSTMENT_RULES = active_rules(ALL_ADJUSTMENT_RULES, REQUIRE_RULE_REVIEW)

LAW_ARTICLES_BY_TYPE = {int(k): v for k, v in load_json('law_articles.json').items()}

VERIFIED_CASES = {int(k): v for k, v in load_json('verified_cases.json').items()}

SURVEY_CONTEXT_OPTIONS = load_json('survey_options.json')

CAUSE_QUESTIONS = {k: [tuple(q) for q in v] for k, v in load_json('cause_questions.json').items()}

CAUSE_KEYS = {k for specs in CAUSE_QUESTIONS.values() for k, _, _ in specs}

# 특정 영상 강제 덮어쓰기: 기본은 꺼져 있다 (dev/confirmed_contexts.json 참고)
CONFIRMED_VIDEO_CONTEXT, CONFIRMED_ROAD_CONTEXT = dev_overrides()
