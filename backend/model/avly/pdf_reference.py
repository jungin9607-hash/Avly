"""CSV-PDF 참고자료 대조. 표준 라이브러리만 사용하며 모델/CSV/규칙을 수정하지 않습니다."""
import argparse
import copy
import csv
import hashlib
import html
import json
import re
from functools import lru_cache
from collections import Counter
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
MODEL_DIR = PACKAGE_DIR.parent
DEFAULT_REFERENCE = PACKAGE_DIR / 'data' / 'pdf_reference_2023' / 'reference.json'
DEFAULT_LINKS = PACKAGE_DIR / 'data' / 'pdf_reference_2023' / 'csv_pdf_links.json'
REQUIRED = {'accident_type', 'accident_object_name', 'accident_place_name',
            'accident_place_feature_name', 'vehicle_a_progress_info_name',
            'vehicle_b_progress_info_name', 'negligence_a', 'negligence_b'}
STATUS = {'document_link_checked': '자료 대응 확인 · 사고 적용은 별도',
          'csv_changed': 'CSV 변경 · 연결 재검토', 'source_changed': '원문 변경 · 연결 재검토',
          'base_mismatch': '기본비율 불일치', 'chart_missing': '연결 도표 없음',
          'unreviewed': '대응 미검토'}


READABLE_STATUSES = {'document_link_checked', 'condition_derived_reference',
                     'source_condition_review', 'base_mismatch', 'source_conflict'}
STATUS.update({'condition_derived_reference': '조건 가감이 CSV 기본값에 포함됨',
               'source_condition_review': '진행·적용 조건 추가 확인',
               'source_conflict': 'PDF 표·설명 수치 충돌',
               'source_proof_invalid': '원문 가감 근거 변경 · 재검토'})


def load_json(path):
    with Path(path).open(encoding='utf-8-sig') as f:
        return json.load(f)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def find_csv(explicit=None, model_dir=None):
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.is_file():
            raise FileNotFoundError('지정한 CSV가 없습니다: ' + str(p))
        return p
    root = Path(model_dir or MODEL_DIR)
    # 분리형 모델이 실제 기본값으로 쓰는 사본을 먼저 선택합니다.
    for p in [root/'avly/data/fault_table_car_to_car.csv', root/'data/fault_table_car_to_car.csv']:
        if p.is_file():
            return p.resolve()
    raise FileNotFoundError('CSV를 찾지 못했습니다. --csv로 경로를 지정하세요.')


def read_rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if REQUIRED - set(reader.fieldnames or []):
            raise ValueError('필수 CSV 열 누락: ' + ', '.join(sorted(REQUIRED-set(reader.fieldnames or []))))
        rows = list(reader)
    seen = set()
    for row in rows:
        key = int(row['accident_type'])
        if key in seen:
            raise ValueError('중복 accident_type: ' + str(key))
        seen.add(key)
        if row['accident_object_name'] != '차대차':
            raise ValueError('차대차 외 행이 있습니다. 차대차 CSV를 지정하세요: ' + str(key))
        pair = [int(row['negligence_a']), int(row['negligence_b'])]
        if any(x < 0 or x > 100 for x in pair) or sum(pair) != 100:
            raise ValueError('기본비율 검증 실패: CSV ' + str(key))
    return sorted(rows, key=lambda r: int(r['accident_type']))


def load_reference(path):
    path = Path(path).resolve()
    info = path.stat()
    return _cached_reference(str(path), info.st_mtime_ns, info.st_size)


@lru_cache(maxsize=2)
def _cached_reference(path, mtime_ns, file_size):
    raw = load_json(path)
    # 모델 조회에는 텍스트만 유지합니다. 그림/PDF 원본은 파일 안에 보존됩니다.
    raw.pop('assets', None)
    raw.pop('original_supporting_files', None)
    charts = raw.get('charts')
    if not isinstance(charts, list) or not charts:
        raise ValueError('charts 배열이 있는 통합 JSON이 필요합니다.')
    ids = [c['official_chart_id'] for c in charts]
    if len(set(ids)) != len(ids):
        raise ValueError('통합 JSON에 중복 도표 번호가 있습니다.')
    return raw, {c['official_chart_id']: c for c in charts}


def pdf_pairs(chart, csv_a_pdf_role='A', variant=None):
    pairs = []
    for p in chart.get('base_fault_candidates', []):
        if variant is not None and p.get('variant_label') != variant:
            continue
        if not all(isinstance(p.get(k), (int, float)) for k in ('A', 'B')):
            continue
        pair = [p['A'], p['B']] if csv_a_pdf_role == 'A' else [p['B'], p['A']]
        if pair not in pairs:
            pairs.append(pair)
    return pairs


def searchable(text):
    text = text.replace('차로변경', '진로변경')
    return re.sub(r'[^가-힣a-z0-9]', '', text.lower())


def grams(text):
    return {text[i:i+2] for i in range(max(0, len(text)-1))}


def lexical_candidates(row, charts, limit=3):
    """검토용 순위만 제공합니다. 확률/정확도나 자동 매핑이 아닙니다."""
    query = searchable(' '.join(row.get(k, '') for k in (
        'accident_place_feature_name', 'vehicle_a_progress_info_name', 'vehicle_b_progress_info_name')))
    q = grams(query)
    if not q:
        return []
    candidates = []
    location = row.get('accident_place_name', '')
    for chart in charts.values():
        text = chart.get('title', '')+' '+' '.join(chart.get('vehicle_roles', {}).values())
        scope = text+' '+chart.get('sections', {}).get('accident_situation', '')
        if '주차' in location and '주차' not in scope:
            continue
        if '회전교차로' in location and '회전교차로' not in scope:
            continue
        words = grams(searchable(text))
        overlap = q & words
        if len(overlap) < 2:
            continue
        score = len(overlap) / max(1, len(q | words))
        candidates.append((score, chart))
    candidates.sort(key=lambda x: (-x[0], x[1]['official_chart_id']))
    return [{'rank': i+1, 'official_chart_id': c['official_chart_id'], 'title': c['title'],
             'vehicle_roles': c.get('vehicle_roles'), 'base_fault_candidates': c.get('base_fault_candidates'),
             'status': 'unverified_lexical_candidate',
             'notice': '문자 유사 검색 후보입니다. 역할·유형·수치의 대응이 확인되지 않아 기본 조회에는 연결하지 않습니다.'}
            for i, (_, c) in enumerate(candidates[:limit])]


def compare_row(row, charts, links, source_sha256):
    key = int(row['accident_type'])
    seed = next((e for e in links.get('entries', []) if e['csv_accident_type'] == key), None)
    result = {'csv_accident_type': key, 'csv_row': copy.deepcopy(row),
              'csv_base_pair': [int(row['negligence_a']), int(row['negligence_b'])],
              'status': 'unreviewed', 'source_document_link': None,
              'pdf_base_pairs_in_csv_order': [], 'base_pair_matches': None,
              'effective_base_matches': None, 'role_mapping_verified': False,
              'rule_engine_ready': False, 'existing_rule_count': 0,
              'pdf_adjustment_candidate_count': None, 'warnings': [], 'review_candidates': []}
    if seed:
        link = copy.deepcopy(seed['source_document_link'])
        chart = charts.get(link['official_chart_id'])
        changes = {k: {'reviewed': v, 'current': row.get(k)} for k, v in seed['csv_row'].items() if row.get(k) != v}
        result['source_document_link'] = link
        if source_sha256 != links.get('pdf_source_sha256'):
            result['status'] = 'source_changed'
        elif changes:
            result['status'] = 'csv_changed'; result['changed_csv_fields'] = changes
        elif chart is None:
            result['status'] = 'chart_missing'
        else:
            pairs = pdf_pairs(chart, link['csv_A_pdf_role'], link.get('variant_label'))
            relation = link.get('relation', 'direct')
            embedded = link.get('embedded_adjustments', [])
            proof_valid = all(any(r.get('raw_text') == p['raw_text']
                                 and r.get('actor_candidate') == p['pdf_actor']
                                 and r.get('delta_pp_candidate') == p['delta_pp']
                                 for r in chart.get('adjustment_table', {}).get('adjustment_row_candidates', []))
                              for p in embedded)
            effective = []
            for pair in pairs:
                delta = sum(p['delta_pp'] if p['pdf_actor'] == link['csv_A_pdf_role'] else -p['delta_pp'] for p in embedded)
                effective.append([pair[0]+delta, pair[1]-delta])
            matches = result['csv_base_pair'] in pairs
            effective_matches = result['csv_base_pair'] in effective
            if not proof_valid:
                status = 'source_proof_invalid'
            elif relation in ('source_conflict', 'source_condition_review'):
                status = relation
            elif relation == 'condition_derived_reference' and effective_matches:
                status = 'condition_derived_reference'
            else:
                status = 'document_link_checked' if matches else 'base_mismatch'
            result.update(status=status, pdf_base_pairs_in_csv_order=pairs,
                          base_pair_matches=matches, effective_base_pairs_in_csv_order=effective,
                          effective_base_matches=effective_matches, embedded_adjustments=embedded,
                          role_mapping_verified=status in ('document_link_checked','condition_derived_reference'),
                          pdf_adjustment_candidate_count=len(chart.get('adjustment_table', {}).get('adjustment_row_candidates', [])))
            result['warnings'] = list(chart.get('warnings', []))+list(chart.get('adjustment_table', {}).get('warnings', []))
            if relation != 'direct': result['warnings'].append(link.get('notice', '자료 대응 검토 필요'))
            result['pdf_roles_in_csv_order'] = {'CSV_A': chart.get('vehicle_roles', {}).get(link['csv_A_pdf_role']),
                                              'CSV_B': chart.get('vehicle_roles', {}).get(link['csv_B_pdf_role'])}
    if result['status'] not in READABLE_STATUSES:
        result['review_candidates'] = lexical_candidates(row, charts)
    return result


def get_csv_reference(csv_type, csv_path=None, reference_path=None, links_path=None,
                      include_candidates=False):
    """후속 모델 연결용 읽기 함수. 후보는 기본 제외하며 계산 승인을 반환하지 않습니다."""
    rows = read_rows(find_csv(csv_path))
    row = next((r for r in rows if int(r['accident_type']) == int(csv_type)), None)
    if row is None:
        raise KeyError('CSV에 없는 유형: ' + str(csv_type))
    raw, charts = load_reference(reference_path or DEFAULT_REFERENCE)
    source_hash = raw.get('original_collection_metadata', {}).get('source_sha256', raw.get('source_sha256'))
    entry = compare_row(row, charts, load_json(links_path or DEFAULT_LINKS), source_hash)
    documents = []
    if entry['status'] in READABLE_STATUSES:
        documents.append(copy.deepcopy(charts[entry['source_document_link']['official_chart_id']]))
    if not include_candidates:
        entry['review_candidates'] = []
    return {'comparison': entry, 'documents': documents,
            'common_guidance': copy.deepcopy(raw.get('common_guidance', [])) if documents else [],
            'rule_engine_ready': False,
            'notice': '문서 조회입니다. status가 수치·조건 충돌이면 적용 기준으로 확정하지 않습니다. 가감산 자동 계산을 실행하지 않습니다.'}


def html_report(report):
    esc = lambda x: html.escape(str(x))
    rows = []
    for entry in report['entries']:
        row = entry['csv_row']; link = entry['source_document_link'] or {}
        candidates = ' / '.join(c['official_chart_id']+' '+c['title'] for c in entry['review_candidates'])
        cols = [entry['csv_accident_type'], row['accident_place_name']+' / '+row['accident_place_feature_name'],
                row['vehicle_a_progress_info_name']+' / '+row['vehicle_b_progress_info_name'],
                '/'.join(map(str, entry['csv_base_pair'])), STATUS[entry['status']],
                link.get('official_chart_id', '미연결'),
                ('CSV A=표 '+link['csv_A_pdf_role']+', CSV B=표 '+link['csv_B_pdf_role']) if link else '',
                entry['existing_rule_count'], entry['pdf_adjustment_candidate_count'] if entry['pdf_adjustment_candidate_count'] is not None else '미검토',
                candidates or '']
        rows.append('<tr>'+''.join('<td>'+esc(c)+'</td>' for c in cols)+'</tr>')
    heads = ['CSV 번호', '장소 / 유형', 'CSV A / B 진행', '기본 A/B', '대조 상태', 'PDF 도표', '역할 대응', '기존 규칙 수', 'PDF 가감 후보 수', '미검증 검색 후보']
    return '''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CSV와 PDF 대조</title><style>body{font:15px/1.6 system-ui,sans-serif;margin:24px;color:#20333e}input{padding:10px;width:min(600px,95%);font:inherit}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:10px;border:1px solid #dce4e8;text-align:left;vertical-align:top}th{background:#eef5f5;position:sticky;top:0}small{color:#526875}.scroll{overflow-x:auto}.note{background:#fff5dc;padding:14px}h1{font-size:24px}</style><h1>CSV와 PDF 참고자료 대조</h1><p>'''+esc(report['summary'])+'''</p><p class="note">자료 대응 확인은 사고 적용이나 가감 규칙 검증 완료를 뜻하지 않습니다. 미검증 검색 후보는 자동 연결하지 않았습니다. 기존 모델·CSV·규칙은 변경하지 않았습니다.</p><p><small>CSV: '''+esc(report['csv_path'])+'''</small></p><input id="q" placeholder="번호·주차장·차43-2 등 검색" aria-label="대조 결과 검색"><p id="count"></p><div class="scroll"><table><thead><tr>'''+''.join('<th>'+esc(h)+'</th>' for h in heads)+'''</tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div><script>const q=document.getElementById('q'),rows=[...document.querySelectorAll('tbody tr')];function filter(){let n=0;for(const r of rows){r.hidden=!r.textContent.toLowerCase().includes(q.value.toLowerCase());if(!r.hidden)n++;}document.getElementById('count').textContent=n+'개 유형 표시';}q.addEventListener('input',filter);filter();</script></html>'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, help='생략하면 avly/data CSV 우선')
    parser.add_argument('--reference', type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument('--links', type=Path, default=DEFAULT_LINKS)
    parser.add_argument('--rules', type=Path, default=MODEL_DIR/'avly/data/adjustment_rules.json')
    parser.add_argument('--out', type=Path, default=MODEL_DIR/'results/pdf_reference_compare')
    parser.add_argument('--csv-type', type=int, help='한 유형의 연결 자료 조회')
    parser.add_argument('--include-candidates', action='store_true', help='한 유형 조회 시 미검증 검색 후보도 표시')
    args = parser.parse_args(argv)
    if args.csv_type is not None:
        result = get_csv_reference(args.csv_type, args.csv, args.reference, args.links, args.include_candidates)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    csv_path = find_csv(args.csv)
    inputs = [csv_path, args.reference, args.links]
    if args.rules.is_file():
        inputs.append(args.rules)
    source_hashes = {str(p.resolve()): sha256(p) for p in inputs}
    out = args.out.expanduser().resolve()
    names = ['csv_pdf_comparison.json', 'csv_pdf_comparison.csv', 'csv_pdf_comparison.html']
    if any((out/n).resolve() in [p.resolve() for p in inputs] for n in names):
        raise ValueError('입력 파일 경로에 보고서를 쓸 수 없습니다.')
    raw, charts = load_reference(args.reference)
    links = load_json(args.links)
    source_hash = raw.get('original_collection_metadata', {}).get('source_sha256', raw.get('source_sha256'))
    entries = [compare_row(r, charts, links, source_hash) for r in read_rows(csv_path)]
    rules = load_json(args.rules) if args.rules.is_file() else {}
    for e in entries:
        registered = rules.get(str(e['csv_accident_type']), {})
        e['existing_rule_count'] = len(registered.get('rules', []))
        e['existing_rules_chart'] = registered.get('official_chart')
        link = e['source_document_link'] or {}
        if registered and link and registered.get('official_chart') != link.get('official_chart_id'):
            e['warnings'].append('기존 규칙의 도표 번호와 이번 연결이 다릅니다. 검토가 필요합니다.')
    counts = dict(Counter(e['status'] for e in entries))
    checked = counts.get('document_link_checked', 0)
    derived = counts.get('condition_derived_reference', 0)
    summary = f'CSV {len(entries)}개 / PDF {len(charts)}개 / 기본값 대응 {checked}개 / 조건 가감 포함 대응 {derived}개 / 추가 검토 {len(entries)-checked-derived}개'
    warnings = []
    copies = [MODEL_DIR/'data/fault_table_car_to_car.csv', MODEL_DIR/'avly/data/fault_table_car_to_car.csv']
    if all(p.is_file() for p in copies) and sha256(copies[0]) != sha256(copies[1]):
        warnings.append('model/data와 model/avly/data의 CSV가 서로 다릅니다. 실제 분석에 쓰는 --csv를 지정하세요.')
    report = {'schema_version':'avly_csv_pdf_comparison_v1', 'csv_path':str(csv_path.resolve()),
              'reference_path':str(args.reference.resolve()), 'source_hashes':source_hashes,
              'summary':summary, 'status_counts':counts, 'warnings':warnings,
              'rule_engine_ready':False, 'entries':entries}
    # 읽기 중 원본이 바뀌면 혼합된 보고서를 저장하지 않습니다.
    if any(sha256(Path(p)) != h for p, h in source_hashes.items()):
        raise RuntimeError('실행 중 입력 자료가 변경됐습니다. 다시 대조하세요.')
    out.mkdir(parents=True, exist_ok=True)
    (out/names[0]).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with (out/names[1]).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['CSV번호', '장소', '사고유형', 'CSV_A진행', 'CSV_B진행', 'CSV_A기본', 'CSV_B기본',
                         '대조상태', 'PDF도표', 'CSV_A의PDF역할', 'CSV_B의PDF역할', '기본비율일치', '기존규칙수', 'PDF가감후보수', '미검증후보'])
        for e in entries:
            r=e['csv_row']; link=e['source_document_link'] or {}
            writer.writerow([e['csv_accident_type'],r['accident_place_name'],r['accident_place_feature_name'],
                             r['vehicle_a_progress_info_name'],r['vehicle_b_progress_info_name'],r['negligence_a'],r['negligence_b'],
                             STATUS[e['status']],link.get('official_chart_id',''),link.get('csv_A_pdf_role',''),link.get('csv_B_pdf_role',''),
                             e['base_pair_matches'],e['existing_rule_count'],e['pdf_adjustment_candidate_count'],
                             ' / '.join(c['official_chart_id'] for c in e['review_candidates'])])
    (out/names[2]).write_text(html_report(report), encoding='utf-8')
    print(summary)
    print('모델·CSV·기존 규칙은 수정하지 않았습니다. 미검증 후보를 자동 계산에 쓰지 마세요.')
    for warning in warnings:
        print('주의:', warning)
    for name in names:
        print(out/name)




def _mapped_rows(chart, link, dashcam_role):
    """PDF 표 → CSV 표 → 서비스 차량 순서로 대응. 미확정은 None입니다."""
    mapped = []
    inverse = {link['csv_A_pdf_role']: 'A', link['csv_B_pdf_role']: 'B'}
    for row in chart.get('adjustment_table', {}).get('adjustment_row_candidates', []):
        pdf_actor = row.get('actor_candidate')
        csv_actor = inverse.get(pdf_actor)
        service_actor = None
        if csv_actor and dashcam_role in ('A', 'B'):
            service_actor = 'A' if csv_actor == dashcam_role else 'B'
        mapped.append({**copy.deepcopy(row), 'pdf_table_actor': pdf_actor,
                       'csv_table_actor': csv_actor, 'service_actor': service_actor,
                       'already_in_csv_base': any(p.get('raw_text') == row.get('raw_text') for p in link.get('embedded_adjustments', [])),
                       'may_apply_again': not any(p.get('raw_text') == row.get('raw_text') for p in link.get('embedded_adjustments', [])),
                       'mapping_scope': '시나리오 역할 가정에 따른 대응; 영상 사실 확인과 별도'})
    return mapped


def attach_pdf_reference(bundle, csv_path=None, reference_path=None, links_path=None):
    """기존 계산을 보존하면서 원문 근거를 붙입니다. API/LLM을 호출하지 않습니다."""
    out = bundle.get('rule_engine_output', {})
    scenarios = {s['scenario_id']: s for s in bundle.get('rule_engine_input', {}).get('scenarios', [])}
    context = {'version': 'avly-pdf-reference-v1', 'edition': '2023-06',
               'status': 'no_scenarios', 'entries': [], 'documents': [],
               'rule_engine_ready': False, 'calculation_modified': False,
               'notice': 'PDF 추출 후보는 참고 근거입니다. 기존 등록 규칙으로만 계산하며 판본·예외·수치 검토는 별도입니다.'}
    bundle['pdf_reference_context'] = context
    if not out.get('results'):
        return bundle
    seen, lookups = set(), {}
    for result in out['results']:
        key = int(result['accident_type'])
        if key not in lookups:
            try:
                lookups[key] = get_csv_reference(key, csv_path, reference_path, links_path)
            except (OSError, ValueError, KeyError) as exc:
                lookups[key] = {'comparison': {'csv_accident_type': key, 'status': 'reference_unavailable',
                                'reason': type(exc).__name__, 'rule_engine_ready': False}, 'documents': []}
            context['entries'].append(lookups[key]['comparison'])
        ref = lookups[key]
        comparison = ref['comparison']
        source = {'status': comparison['status'], 'csv_accident_type': key,
                  'edition': '2023-06', 'calculation_modified': False,
                  'rule_engine_ready': False}
        result['pdf_reference'] = source
        if not ref['documents']:
            continue
        chart = ref['documents'][0]
        link = comparison['source_document_link']
        scenario = scenarios.get(result.get('scenario_id'), {})
        mapped = _mapped_rows(chart, link, scenario.get('dashcam_table_role') if comparison.get('role_mapping_verified') else None)
        source.update(official_chart_id=chart['official_chart_id'],
                      csv_A_pdf_role=link['csv_A_pdf_role'], csv_B_pdf_role=link['csv_B_pdf_role'],
                      source=copy.deepcopy(chart.get('source')),
                      source_pages=[{'pdf_page': p['pdf_page'], 'printed_page': p['printed_page']}
                                    for p in chart.get('source_pages', [])],
                      adjustment_candidates=mapped,
                      actor_mapping_confirmed=bool(scenario.get('eligible_for_adjustment') and comparison.get('role_mapping_verified')),
                      warnings=copy.deepcopy(comparison.get('warnings', [])))
        if chart['official_chart_id'] not in seen:
            seen.add(chart['official_chart_id'])
            context['documents'].append(chart)
        # 수치와 역할뿐 아니라 원문 항목명도 대응할 때에만 해당 행을 근거로 표시합니다.
        for section in ('applied_adjustments', 'pending', 'not_applied'):
            for factor in result.get(section, []):
                label = searchable(factor.get('label', '').replace('주차장 ', ''))
                matches = [r for r in mapped if label and label in searchable(r.get('raw_text', ''))
                           and r['service_actor'] == factor.get('actor')
                           and r.get('delta_pp_candidate') == factor.get('delta_pp')
                           and not r.get('not_applicable')]
                factor['pdf_source_evidence'] = {
                    'status': 'text_role_value_match' if matches else 'manual_review_needed',
                    'official_chart_id': chart['official_chart_id'],
                    'rows': [r['raw_text'] for r in matches],
                    'notice': '추출 원문과 항목명·역할·수치의 대응입니다. 적용 사실이나 계산 규칙 승인과 다릅니다.'}
    statuses = [e['status'] for e in context['entries']]
    context['status'] = ('linked' if all(s in ('document_link_checked','condition_derived_reference') for s in statuses)
                         else 'partial' if any(s in READABLE_STATUSES for s in statuses)
                         else 'unmapped_or_unavailable')
    return bundle


def pdf_report_lines(context):
    if not context or context.get('status') == 'no_scenarios':
        return []
    ids = [d['official_chart_id'] for d in context.get('documents', [])]
    lines = ['PDF 참고 기준: ' + ' / '.join(ids) + ' · 2023.06 원문' ] if ids else []
    pending = [str(e['csv_accident_type']) for e in context.get('entries', [])
               if e['status'] not in ('document_link_checked','condition_derived_reference')]
    if pending:
        lines.append('  PDF 대응 확인 필요: CSV ' + ', '.join(pending) + '번')
    if ids:
        lines.append('  원문 해설·가감 후보를 JSON에 첨부했습니다. 계산은 기존 등록 규칙을 사용합니다.')
    return lines



def web_pdf_reference(csv_type, dashcam_role, csv_path=None):
    """웹 설문 확정 후에도 현재 CSV로 다시 조회하는 간결한 참고 근거."""
    if csv_type is None:
        return {'status':'no_scenarios','documents':[],'calculation_modified':False}
    try:
        ref = get_csv_reference(csv_type, csv_path)
    except (OSError, ValueError, KeyError) as exc:
        return {'status':'reference_unavailable','reason':type(exc).__name__,
                'documents':[],'calculation_modified':False}
    comparison = ref['comparison']; link = comparison.get('source_document_link') or {}
    documents = []
    for chart in ref['documents']:
        factors = _mapped_rows(chart, link, dashcam_role if comparison.get('role_mapping_verified') else None)
        documents.append({'official_chart_id':chart['official_chart_id'],'title':chart['title'],
                          'vehicle_roles':chart['vehicle_roles'],
                          'pdf_base_pairs_in_csv_order':comparison['pdf_base_pairs_in_csv_order'],
                          'csv_base_pair':comparison['csv_base_pair'],
                          'service_base_pair':comparison['csv_base_pair'] if dashcam_role=='A' else list(reversed(comparison['csv_base_pair'])) if dashcam_role=='B' else None,
                          'pdf_base_pairs_in_service_order':[p if dashcam_role=='A' else list(reversed(p)) for p in comparison['pdf_base_pairs_in_csv_order']] if dashcam_role in ('A','B') else [],
                          'source_pages':[{'pdf_page':p['pdf_page'],'printed_page':p['printed_page']} for p in chart.get('source_pages',[])],
                          'adjustment_candidates':factors,
                          'explanations':{k:chart.get('sections',{}).get(k,'') for k in
                                          ('accident_situation','base_fault_explanation','adjustment_explanation','application_notes')},
                          'source':chart.get('source')})
    return {'status':comparison['status'],'status_label':{
                'document_link_checked':'선택한 사고 유형과 기본비율이 원문에 대응해요.',
                'condition_derived_reference':'일부 진행 조건이 기본비율에 이미 반영되어 있어요.',
                'source_condition_review':'원문과 진행 조건을 추가로 확인해야 해요.',
                'base_mismatch':'선택 유형과 원문의 기본비율이 달라 확인이 필요해요.',
                'source_conflict':'원문 표와 해설의 수치가 달라 추가 확인이 필요해요.'
            }.get(comparison['status'],'자료 확인 필요'),
            'edition':'2023-06','csv_accident_type':int(csv_type),'documents':documents,
            'source_document_link':link,'warnings':comparison.get('warnings',[]),
            'embedded_adjustments':comparison.get('embedded_adjustments',[]),
            'calculation_modified':False,'rule_engine_ready':False,
            'notice':'PDF 참고 근거입니다. 아래 후보 전체가 계산에 반영된 것은 아닙니다. 계산은 등록된 규칙과 확인한 답변에 따릅니다.'}


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError) as exc:
        raise SystemExit('대조 실패: ' + str(exc)) from None
