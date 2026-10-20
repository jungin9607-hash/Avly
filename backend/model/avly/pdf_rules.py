"""PDF 표에서 만든 설문 규칙을 조회합니다. 타입·판본·CSV 대응이 맞을 때만 사용합니다."""
import copy
import re
from functools import lru_cache
from pathlib import Path

from .tables import ADJUSTMENT_RULES, FACTOR_LABELS
from .pdf_reference import get_csv_reference, load_json

RULE_PATH=Path(__file__).resolve().parent/'data/pdf_survey_rules.json'


@lru_cache(maxsize=2)
def _load(path,mtime,size):
    return load_json(path)


def registry():
    p=RULE_PATH;stat=p.stat()
    return _load(str(p),stat.st_mtime_ns,stat.st_size)


def factor_label(factor):
    try:return registry()['factor_labels'].get(factor,FACTOR_LABELS.get(factor,factor))
    except (OSError,ValueError,KeyError):return FACTOR_LABELS.get(factor,factor)


def get_rule_config(type_id,csv_path=None):
    key=str(type_id)
    try:
        config=registry()['types'].get(key)
        if config is not None:
            ref=get_csv_reference(type_id,csv_path=csv_path)
            c=ref['comparison']
            if c['status'] in ('document_link_checked','condition_derived_reference') and c['csv_row']==config['source_csv_row']:
                return copy.deepcopy(config)
            return None
    except (OSError,ValueError,KeyError):
        pass
    return copy.deepcopy(ADJUSTMENT_RULES.get(key))


def registered_types(csv_path=None):
    try:keys=set(registry()['types'])|set(ADJUSTMENT_RULES)
    except (OSError,ValueError,KeyError):keys=set(ADJUSTMENT_RULES)
    return sorted(int(k) for k in keys if get_rule_config(k,csv_path) is not None)


def rule_display(rule,who):
    from .explain import explain_factor
    e=explain_factor(rule['factor'],rule['delta_pp'],who)
    if e['missing']:
        label=rule.get('label') or factor_label(rule['factor'])
        e.update(title=label,easy=label+'에 해당하는 상황이 실제 있었는지 확인해 주세요.',
                 question=f"{who}에 ‘{label}’에 해당하는 상황이 있었나요?")
    source = rule.get('pdf_source')
    if source:
        label = re.sub(r'^\s*(?:(?:[①-⑳]|\([가-라]\))\s*)*[AB]\s*', '', source['raw_text'])
        label = re.sub(r'\s*[+−–-]\s*\d+(?:\s*[%％](?:p)?)?\s*$', '', label).strip()
        e.update(title=label, question=f"{who} · {label}", pdf_factor=label)
    if rule['factor'] in ('gross_negligence','serious_negligence'):
        e['easy']=(e.get('easy') or '')+' 다른 질문에 답한 것과 같은 행동을 중복으로 선택하지 마세요.'
    return e
