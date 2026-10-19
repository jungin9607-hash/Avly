"""기본 과실비율과 가감요소를 쉬운 말로 설명한다.

AI 를 쓰지 않는다. data/adjustment_explanations.json 의 문장에 값을 끼워 넣어 만든다.
같은 요소는 항상 같은 설명이 나오고, 법적 설명을 AI 가 지어낼 위험이 없다.
JSON 의 문장은 AI 가 쓴 초안이며 사람이 검수해야 한다 (항목별 reviewed).
"""
from .dataio import load_json
from .tables import FACTOR_LABELS

WHO = ('내 차', '상대 차')
_cache = None


def _data():
    global _cache
    if _cache is None:
        _cache = load_json('adjustment_explanations.json')
    return _cache


def _number(value):
    value = abs(value)
    return int(value) if float(value).is_integer() else value


def explain_base(base_me, base_other, place=None, my_progress=None, other_progress=None):
    """기본 비율 설명. 장소와 진행 정보를 알면 상황 문장도 붙인다."""
    templates = _data()['templates']
    result = {'text': templates['base'].format(me=_number(base_me), other=_number(base_other)), 'situation': None}
    if place and my_progress and other_progress:
        result['situation'] = templates['situation'].format(place=place, my_progress=my_progress, other_progress=other_progress)
    return result


def explain_factor(factor_id, delta_pp, who):
    """가감요소 하나를 설명한다. who 는 '내 차' 또는 '상대 차', delta_pp 는 그 쪽 과실의 가감(%p, 0 이 아님).

    사전에 없는 요소는 공식 이름만 돌려주고 missing=True 로 표시한다.
    """
    if who not in WHO:
        raise ValueError("who 는 '내 차' 또는 '상대 차' 여야 합니다: %r" % (who,))
    if not delta_pp:
        raise ValueError('delta_pp 는 0 이 아니어야 합니다.')
    templates = _data()['templates']
    effect = templates['effect_up' if delta_pp > 0 else 'effect_down'].format(who=who, n=_number(delta_pp))
    entry = _data()['factors'].get(factor_id)
    if entry is None:
        return {'factor': factor_id, 'title': FACTOR_LABELS.get(factor_id, factor_id), 'easy': None, 'question': None,
                'effect': effect, 'reviewed': False, 'missing': True}
    return {'factor': factor_id, 'title': entry['title'], 'easy': entry['easy'], 'question': entry['question'].format(who=who),
            'effect': effect, 'reviewed': entry['reviewed'], 'missing': False}


def explain_law(article):
    """도로교통법 조문 번호(예: 19, '25의2')의 이름과 쉬운 풀이. 작성 전이면 name, easy 가 None 이다."""
    entry = _data()['laws'].get(str(article))
    if entry is None:
        return {'article': str(article), 'name': None, 'easy': None, 'reviewed': False, 'missing': True}
    return {'article': str(article), 'name': entry['name'], 'easy': entry['easy'], 'reviewed': entry['reviewed'],
            'missing': entry['name'] is None or entry['easy'] is None}
