"""법령/판례 API 조회."""
import hashlib
import html
import json
import re
import requests
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from .constants import CASE_API_ENABLED, CASE_MAX_BODY_REQUESTS, CASE_RELEVANCE_VERSION, CASE_TARGET_COUNT, LAW_ACCIDENT_DATE, LAW_API_ENABLED, LAW_SECRET_NAME
from .tables import LAW_ARTICLES_BY_TYPE, VERIFIED_CASES
from .context import ctx
from .config import get_secret
from .facts import civil_fault_number


def law_list(value):
    return value if isinstance(value, list) else [value] if isinstance(value, dict) else []

def law_text(value):
    if isinstance(value, dict):
        return law_text(value.get('content', ''))
    if isinstance(value, list):
        return '\n'.join((law_text(x) for x in value))
    return str(value) if value is not None else ''

class LawAPIClient:

    def __init__(self, oc, cache_dir, accident_date=None, session=None):
        self.oc = oc
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = session or requests.Session()
        self.accident_date = str(accident_date) if accident_date else None
        if self.accident_date:
            datetime.strptime(self.accident_date, '%Y%m%d')

    def _safe(self, value):
        if isinstance(value, dict):
            return {k: self._safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._safe(v) for v in value]
        if isinstance(value, str):
            value = value.replace(str(self.oc), '[인증값 숨김]') if self.oc else value
            return re.sub('(?i)(OC=)[^&\\s"\\\'<>]+', '\\1[인증값 숨김]', value)
        return value

    def _validate(self, endpoint, data):
        if not isinstance(data, dict):
            raise RuntimeError('법령 JSON 최상위 형식 오류')
        if endpoint == 'lawSearch.do':
            body = data.get('LawSearch', {})
            if not isinstance(body, dict) or str(body.get('resultCode', '00')) != '00':
                raise RuntimeError('법령 검색 API 오류 응답')
            if not law_list(body.get('law')):
                raise RuntimeError('법령 검색 결과 없음')
        else:
            body = data.get('법령', {})
            if not isinstance(body, dict) or not law_list(body.get('조문', {}).get('조문단위')):
                raise RuntimeError('법령 본문 또는 요청 조문을 찾지 못함')
        return data

    def _json(self, endpoint, params):
        public = {'target': 'eflaw', 'type': 'JSON', **params}
        key = hashlib.sha256(json.dumps([endpoint, public], sort_keys=True).encode()).hexdigest()
        path = self.cache_dir / (key + '.json')
        if path.exists() and time.time() - path.stat().st_mtime < 86400:
            try:
                return self._validate(endpoint, json.loads(path.read_text(encoding='utf-8')))
            except (ValueError, RuntimeError, AttributeError):
                pass
        try:
            response = self.session.get('https://www.law.go.kr/DRF/' + endpoint, params={**public, 'OC': self.oc}, timeout=(10, 25))
        except requests.RequestException:
            raise RuntimeError('법령 API 연결 실패 또는 시간 초과') from None
        if response.status_code != 200:
            raise RuntimeError('법령 API HTTP 오류: ' + str(response.status_code))
        try:
            data = response.json()
        except ValueError:
            raise RuntimeError('법령 API가 JSON 대신 안내 페이지를 반환함') from None
        data = self._safe(self._validate(endpoint, data))
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        return data

    def select_law(self, name='도로교통법'):
        found = []
        page = 1
        while True:
            params = {'query': name, 'search': 1, 'nw': '1,3' if self.accident_date else 3, 'display': 100, 'page': page}
            if self.accident_date:
                params['efYd'] = '19000101~' + self.accident_date
            body = self._json('lawSearch.do', params)['LawSearch']
            rows = law_list(body.get('law'))
            for row in rows:
                if law_text(row.get('법령명한글')) != name:
                    continue
                eff = law_text(row.get('시행일자')).replace('-', '')
                if self.accident_date and (not eff or eff > self.accident_date):
                    continue
                found.append({'name': name, 'id': law_text(row.get('법령ID')), 'mst': law_text(row.get('법령일련번호')), 'effective_date': eff, 'promulgation_date': law_text(row.get('공포일자'))})
            total = body.get('totalCnt')
            if total is not None and page * 100 >= int(total):
                break
            if total is None and len(rows) < 100:
                break
            page += 1
        if not found:
            raise RuntimeError('지정 날짜에 대응하는 법령 판본을 찾지 못함')
        selected = max(found, key=lambda r: (r['effective_date'], r['promulgation_date'], int(r['mst'] or 0)))
        if self.accident_date and (not selected['mst'] or not selected['effective_date']):
            raise RuntimeError('연혁 법령의 MST·시행일 정보 없음')
        if not self.accident_date and (not selected['id']):
            raise RuntimeError('현행 법령 ID 없음')
        return selected

    def article(self, number, law=None):
        law = law or self.select_law()
        match = re.fullmatch('(\\d+)(?:의(\\d+))?', str(number))
        if not match:
            raise ValueError('조문 번호 형식 오류')
        main = int(match.group(1))
        branch = int(match.group(2) or 0)
        params = {'JO': f'{main:04d}{branch:02d}'}
        if self.accident_date:
            params.update(MST=law['mst'], efYd=law['effective_date'])
        else:
            params['ID'] = law['id']
        body = self._json('lawService.do', params)['법령']
        articles = law_list(body['조문']['조문단위'])
        article = next((a for a in articles if law_text(a.get('조문번호')).lstrip('0') == str(main) and int(law_text(a.get('조문가지번호', '0')) or 0) == branch), None)
        if article is None:
            raise RuntimeError(f'제{number}조 본문 없음')
        parts = [law_text(article.get('조문내용'))]

        def collect(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in ('항내용', '호내용', '목내용'):
                        parts.append(law_text(value))
                    else:
                        collect(value)
            elif isinstance(node, list):
                for child in node:
                    collect(child)
        collect(article)
        actual_eff = law_text(body.get('기본정보', {}).get('시행일자')) or law['effective_date']
        return {**law, 'effective_date': actual_eff, 'article': number, 'title': law_text(article.get('조문제목')), 'text': '\n'.join((x for x in parts if x)), 'version_basis': '사고일 이전 시행 판본' if self.accident_date else '현행법령 (사고 당시 판본 확인 아님)', 'requested_accident_date': self.accident_date, 'source_url': 'https://www.law.go.kr/DRF/lawService.do?' + urlencode({'target': 'eflaw', 'type': 'JSON', **params})}

def legal_context_for_input(payload, client=None):
    types = sorted({int(s['accident_type']) for s in payload.get('scenarios', [])})
    articles = sorted({n for t in types for n in LAW_ARTICLES_BY_TYPE.get(t, [])}, key=lambda n: tuple((int(x) for x in str(n).split('의'))))
    mapping_mode = '사고 유형 관련 조문'
    if not articles:
        environment_articles = {'주차장': [18], '직선 도로': [19, 38, 48], '교차로': [25, 26, 48], '회전교차로': [19, 48]}
        articles = environment_articles.get(payload.get('road_shape'), [])
        mapping_mode = '관찰 장소의 일반 참고 조문 — 사고 유형 적용 확정 아님'
    if not LAW_API_ENABLED:
        return {'status': 'disabled', 'articles': [], 'errors': []}
    if not articles:
        return {'status': 'not_mapped', 'articles': [], 'errors': [], 'reason': '사고 유형 후보와 관찰 장소에 연결된 조문 없음'}
    result = {'status': 'ok', 'articles': [], 'errors': [], 'format': 'JSON', 'scope': '법적 근거 조회; 가감 수치는 별도의 과실 기준 규칙에서 계산', 'mapping_mode': mapping_mode, 'candidate_count': len(payload.get('scenarios', [])), 'requested_accident_date': LAW_ACCIDENT_DATE}
    try:
        if client is None:
            oc = get_secret(LAW_SECRET_NAME)
            if not oc:
                raise RuntimeError('law_api 비밀값 없음')
            client = LawAPIClient(oc, ctx.result_dir / 'law_api_json_cache', LAW_ACCIDENT_DATE)
        law = client.select_law()
    except Exception:
        result.update(status='unavailable', errors=['JSON 법령 조회 준비 실패: 인증·이용 권한·연결·사고일을 확인하세요.'])
        return result
    for number in articles:
        try:
            result['articles'].append(client.article(number, law))
        except Exception:
            result['errors'].append(f'도로교통법 제{number}조 JSON 조회 실패')
    if result['errors']:
        result['status'] = 'partial' if result['articles'] else 'unavailable'
    return result

def case_plain(value):
    text = law_text(value)
    text = re.sub('<br\\s*/?>', '\n', text, flags=re.I)
    return html.unescape(re.sub('<[^>]*>', ' ', text)).strip()

def case_profile(row):
    text = ' '.join((str(row.get(k, '')) for k in ('accident_place_name', 'accident_place_feature_name', 'vehicle_a_progress_info_name', 'vehicle_b_progress_info_name', 'accident_object_name')))
    families = [('회전교차로', ['회전교차로']), ('주차장', ['주차장', '주차구역', '주차구획']), ('출차', ['출차', '진출']), ('진로변경', ['차로변경', '진로변경']), ('추돌', ['추돌', '안전거리']), ('유턴', ['유턴']), ('역주행', ['역주행']), ('중앙선', ['중앙선']), ('합류', ['합류']), ('후진', ['후진']), ('좌회전', ['좌회전']), ('우회전', ['우회전']), ('교차로', ['교차로']), ('보행자', ['보행자', '횡단보도']), ('자전거', ['자전거']), ('이륜차', ['이륜차', '오토바이'])]
    groups = [(name, words) for name, words in families if any((w in text for w in words))]
    if not groups:
        feature = str(row.get('accident_place_feature_name', '')).strip()
        tokens = [t for t in re.findall('[가-힣]{2,}', feature) if t not in ('사고', '도로', '직선', '있음', '없음', '동일폭')]
        groups = [(t, [t]) for t in tokens[:2]]
    return {'type': row['accident_type'], 'text': text, 'groups': groups, 'queries': list(dict.fromkeys((name for name, words in groups)))[:3] or ['교통사고']}

class CaseAPIClient:

    def __init__(self, oc, cache_dir, session=None):
        self.oc = oc
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = session or requests.Session()

    def safe(self, value):
        if isinstance(value, dict):
            return {k: self.safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.safe(v) for v in value]
        if isinstance(value, str):
            return re.sub('(?i)(OC=)[^&\\s"\\\'<>]+', '\\1[인증값 숨김]', value.replace(str(self.oc), '[인증값 숨김]'))
        return value

    def root(self, data, endpoint):
        if not isinstance(data, dict):
            raise RuntimeError('판례 JSON 형식 오류')
        bodies = [data] + [v for v in data.values() if isinstance(v, dict)]
        for body in bodies:
            if endpoint == 'lawSearch.do' and ('prec' in body or 'totalCnt' in body):
                if str(body.get('resultCode', '00')) not in ('00', '0'):
                    raise RuntimeError('판례 목록 서비스 오류')
                return body
            if endpoint == 'lawService.do' and body.get('사건번호') and (body.get('판례내용') or body.get('판결요지') or body.get('판시사항')):
                return body
        raise RuntimeError('판례 조회 응답 확인 필요')

    def fetch(self, endpoint, params):
        public = {'target': 'prec', 'type': 'JSON', **params}
        key = hashlib.sha256(json.dumps([endpoint, public], sort_keys=True).encode()).hexdigest()
        path = self.cache_dir / (key + '.json')
        if path.exists() and time.time() - path.stat().st_mtime < 86400:
            try:
                return self.root(json.loads(path.read_text(encoding='utf-8')), endpoint)
            except (ValueError, RuntimeError):
                pass
        try:
            response = self.session.get('https://www.law.go.kr/DRF/' + endpoint, params={**public, 'OC': self.oc}, timeout=(10, 20))
        except requests.RequestException:
            raise RuntimeError('판례 API 연결 실패 또는 시간 초과') from None
        if response.status_code != 200:
            raise RuntimeError('판례 API HTTP ' + str(response.status_code))
        try:
            data = response.json()
        except ValueError:
            raise RuntimeError('판례 API가 JSON 대신 안내 페이지 반환: 판례 목록·본문 권한 확인 필요') from None
        self.root(data, endpoint)
        data = self.safe(data)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        return self.root(data, endpoint)

    def search(self, query):
        body = self.fetch('lawSearch.do', {'search': 2, 'query': query, 'display': 8, 'page': 1, 'sort': 'ddes'})
        return law_list(body.get('prec'))

    def detail(self, identifier):
        return self.fetch('lawService.do', {'ID': str(identifier)})

def match_case_body_v219(body, profile):
    primary = case_plain(body.get('사건명', '')) + ' ' + case_plain(body.get('판결요지', '')) + ' ' + case_plain(body.get('판시사항', ''))
    full = case_plain(body.get('판례내용', ''))
    text = primary + ' ' + full
    traffic = bool(re.search('교통사고|추돌|충돌', text))
    matched = [name for name, words in profile['groups'] if any((w in text for w in words))]
    if not traffic or (profile['groups'] and (not matched)):
        return None
    location = [x for x in profile['groups'] if x[0] in ('주차장', '회전교차로')]
    if location and (not all((name in matched for name, words in location))):
        return None
    mechanisms = [x for x in profile['groups'] if x[0] not in ('주차장', '회전교차로', '교차로')]
    if mechanisms and (not any((name in matched for name, words in mechanisms))):
        return None
    sentences = [s.strip() for s in re.split('\\n+|(?<=[.!?])\\s+', primary + '\n' + full) if s.strip()]
    relevant = next((s for s in sentences if any((w in s for name, words in profile['groups'] for w in words))), None)
    excerpt = (relevant or primary or full)[:400]
    if not excerpt:
        return None
    number = case_plain(body.get('사건번호'))
    court = case_plain(body.get('법원명'))
    date = case_plain(body.get('선고일자'))
    if not number or not court or (not date):
        return None
    identifier = law_text(body.get('판례정보일련번호') or body.get('판례일련번호'))
    return {'court': court, 'date': date, 'case_number': number, 'summary': excerpt, 'comparison_limit': '검색 일치 조건: ' + (' / '.join(matched) or '교통사고') + '; 신호·진행·접촉 위치·위반 사정이 실제 영상과 같은지는 별도 검토가 필요하며 비율을 자동 적용하지 않음.', 'source': 'https://www.law.go.kr/DRF/lawService.do?' + urlencode({'target': 'prec', 'ID': identifier, 'type': 'JSON'}), 'source_kind': '국가법령정보 공동활용 판례 본문에서 발췌; 키워드 기반 참고 후보', 'matched_terms': matched, 'relevance_status': 'keyword_reference', 'case_api_id': identifier, 'score': len(matched) * 2 + sum((2 for name, words in profile['groups'] if any((w in primary for w in words))))}

def case_search_queries(profile):
    """사고 조건 단어를 한꺼번에 담은 검색어를 먼저, 단어 하나짜리 검색어를 나중에 쓴다. (한 단어만 검색하면 형사 사건이 대부분이다)"""
    names = [name for name, words in profile['groups']][:3]
    combined = [' '.join(names) + ' 과실', ' '.join(names) + ' 과실비율', '교통사고 ' + ' '.join(names) + ' 손해배상 과실'] if names else []
    return list(dict.fromkeys(combined + profile['queries']))

def related_cases_for_row(row, client=None):
    profile = case_profile(row)
    queries = case_search_queries(profile)
    seeds = [dict(c) for c in VERIFIED_CASES.get(row['accident_type'], [])]
    audit = {'accident_type': row['accident_type'], 'target_count': CASE_TARGET_COUNT, 'queries': queries, 'source': '판례 본문 검색 + 유형별 등록 자료', 'status': 'ok', 'errors': []}
    if len(seeds) >= CASE_TARGET_COUNT:
        return (seeds[:CASE_TARGET_COUNT], {**audit, 'status': 'registered_complete', 'count': CASE_TARGET_COUNT})
    if not CASE_API_ENABLED:
        return (seeds, {**audit, 'status': 'disabled', 'count': len(seeds), 'reason': '판례 API 비활성'})
    try:
        if client is None:
            oc = get_secret(LAW_SECRET_NAME)
            if not oc:
                raise RuntimeError('law_api 비밀값 없음')
            client = CaseAPIClient(oc, ctx.result_dir / 'case_api_cache')
        seen = {re.sub('\\s+', '', c['case_number']) for c in seeds}
        seen_ids = set()
        found = []
        partial = []
        attempts = 0
        for query in queries:
            for item in client.search(query):
                identifier = law_text(item.get('판례일련번호') or item.get('판례정보일련번호'))
                number = re.sub('\\s+', '', law_text(item.get('사건번호')))
                if not identifier or identifier in seen_ids or (number and number in seen):
                    continue
                if attempts >= CASE_MAX_BODY_REQUESTS:
                    break
                seen_ids.add(identifier)
                attempts += 1
                try:
                    body = client.detail(identifier)
                except Exception:
                    audit['errors'].append('판례 본문 조회 실패')
                    continue
                case = match_case_body(body, profile)
                if not case:
                    partial_case = match_case_body_partial(body, profile)
                    if partial_case and (not partial_case['case_api_id']):
                        partial_case['case_api_id'] = identifier
                        partial_case['source'] = 'https://www.law.go.kr/DRF/lawService.do?' + urlencode({'target': 'prec', 'ID': identifier, 'type': 'JSON'})
                    if partial_case and re.sub('\\s+', '', partial_case['case_number']) not in seen:
                        partial.append(partial_case)
                    continue
                if not case['case_api_id']:
                    case['case_api_id'] = identifier
                    case['source'] = 'https://www.law.go.kr/DRF/lawService.do?' + urlencode({'target': 'prec', 'ID': identifier, 'type': 'JSON'})
                key = re.sub('\\s+', '', case['case_number'])
                if key in seen:
                    continue
                seen.add(key)
                found.append(case)
            if len(seeds) + len(found) >= CASE_TARGET_COUNT or attempts >= CASE_MAX_BODY_REQUESTS:
                break
        selected = (seeds + sorted(found, key=lambda c: c['score'], reverse=True))[:CASE_TARGET_COUNT]
        if len(selected) < CASE_TARGET_COUNT:
            # 엄격한 기준을 통과한 판례가 모자라면, 일부 조건만 맞는 판례를 비슷한 순서로 채운다 (표시는 '일부 일치'로 구분)
            chosen = {re.sub('\\s+', '', c['case_number']) for c in selected}
            extra = []
            for c in sorted(partial, key=lambda c: c['score'], reverse=True):
                number = re.sub('\\s+', '', c['case_number'])
                if number not in chosen:
                    chosen.add(number)
                    extra.append(c)
            selected = selected + extra[:CASE_TARGET_COUNT - len(selected)]
        audit.update(count=len(selected), body_requests=attempts, status='ok' if len(selected) == CASE_TARGET_COUNT else 'insufficient')
        if len(selected) < CASE_TARGET_COUNT:
            audit['reason'] = '관련 본문·중복 검토를 통과한 자료가 목표3개보다 적음; 조건이 전혀 맞지 않는 판례로는 채우지 않음'
        return (selected, audit)
    except Exception:
        audit.update(status='unavailable', count=len(seeds), reason='판례 검색 실패: law_api의 판례 목록·본문 조회 이용 권한 또는 연결을 확인하세요.')
        return (seeds, audit)

def law_article_label(number):
    parts = str(number).split('의')
    return '제' + parts[0] + '조' + ('의' + parts[1] if len(parts) > 1 else '')

def match_case_body(body, profile):
    number = case_plain(body.get('사건번호', ''))
    if re.search('\\d(?:도|노|고합|고단|고정|구합|구단)', number):
        return None
    text = ' '.join((case_plain(body.get(k, '')) for k in ('사건명', '판결요지', '판시사항', '판례내용')))
    if not re.search('손해배상|과실상계|과실비율|배상책임', text):
        return None
    if not re.search('차량\\s*간|차대차|양\\s*차량|선행차|후행차|앞차|뒤차|상대\\s*차량|원고\\s*차량|피고\\s*차량', text):
        return None
    for name, words in profile['groups']:
        if name in ('주차장', '회전교차로') and (not any((w in text for w in words))):
            return None
    if '차도와 차도가 아닌' in profile['text'] and (not re.search('노외|차도가 아닌|도로로 진입|주차장.{0,20}도로', text)):
        return None
    mechanisms = [words for name, words in profile['groups'] if name not in ('교차로', '주차장', '회전교차로')]
    if mechanisms and (not all((any((w in text for w in words)) for words in mechanisms))):
        return None
    result = match_case_body_v219(body, profile)
    if result:
        result['relevance_status'] = 'civil_traffic_context_reference'
        result['comparison_limit'] = '차대차 손해배상·사고 쟁점 검색을 통과한 참고 자료이며 실제 사정·과실비율의 일치를 뜻하지 않음'
    return result

def case_date(value):
    v = str(value)
    return v[:4] + '-' + v[4:6] + '-' + v[6:] if re.fullmatch('\\d{8}', v) else v

def case_identity(case):
    return (re.sub(r'\s+', '', str(case.get('court', ''))),
            re.sub(r'\s+', '', str(case.get('case_number', ''))),
            re.sub(r'[^0-9]', '', str(case.get('date', ''))))

def match_case_body(body,profile):
    number=case_plain(body.get('사건번호',''))
    if not civil_fault_number(number):return None
    title=case_plain(body.get('사건명',''))
    if not re.search(r'손해배상|구상금|보험금|채무부존재',title):return None
    text=' '.join(case_plain(body.get(k,'')) for k in ('판시사항','판결요지','판례내용'))
    if not re.search(r'과실|안전거리|전방주시|주의의무|배상책임|손해배상',text):return None
    pair=r'차량\s*간|차대차|양\s*차량|선행차|후행차|앞차|뒤차|상대\s*차량|원고\s*차량|피고\s*차량'
    contexts=[]
    for anchor in re.finditer(r'교통사고|추돌|충돌|충격',text):
        block=text[max(0,anchor.start()-300):anchor.end()+300]
        if not re.search(pair,block):continue
        groups=[words for name,words in profile['groups'] if name!='교차로']
        if groups and not all(any(word in block for word in words) for words in groups):continue
        contexts.append(block.strip())
    if not contexts:return None
    if '차도와 차도가 아닌' in profile['text'] and not re.search(r'노외|차도가 아닌|도로로 진입|주차장.{0,20}도로',text):return None
    result=match_case_body_v219(body,profile)
    if not result:return None
    result.update(summary=contexts[0][:400], case_name=title,
        relevance_status=CASE_RELEVANCE_VERSION,
        relevance_checks={'civil_case':True,'claim_subject':True,'vehicle_collision_context':True,'location_and_mechanism':True},
        comparison_limit='차량 간 충돌과 민사 배상 쟁점을 본문에서 함께 확인한 참고 사례입니다. 사고 경로·차량 역할·회피 가능성과 비율은 별도 비교가 필요합니다.')
    return result

def match_case_body_partial(body, profile):
    """엄격한 기준(match_case_body)은 통과하지 못했지만 일부 조건이 맞는 판례. 상위 순위를 채우는 데만 쓴다.

    지키는 것: 민사 과실 사건, 손해배상 등 청구, 과실·주의의무 쟁점, 교통사고 문맥, 장소·사고 방식 조건 중 최소 하나. 주차장·회전교차로는 반드시 맞아야 한다.
    풀어 준 것: 모든 조건이 같은 문단 안에서 함께 나와야 한다는 요구, 차량 간 표현 요구, 사고 방식 조건이 없어도 되는 것.
    """
    number = case_plain(body.get('사건번호', ''))
    if not civil_fault_number(number):
        return None
    title = case_plain(body.get('사건명', ''))
    if not re.search(r'손해배상|구상금|보험금|채무부존재', title):
        return None
    text = ' '.join((case_plain(body.get(k, '')) for k in ('판시사항', '판결요지', '판례내용')))
    if not re.search(r'과실|안전거리|전방주시|주의의무|배상책임|손해배상', text):
        return None
    if not re.search(r'교통사고|추돌|충돌|충격', text):
        return None
    matched_groups = [(name, words) for name, words in profile['groups'] if any((w in text for w in words))]
    if not matched_groups:
        return None
    hard = [name for name, words in profile['groups'] if name in ('주차장', '회전교차로')]
    if hard and not all((name in [m[0] for m in matched_groups] for name in hard)):
        return None
    result = match_case_body_v219(body, {**profile, 'groups': matched_groups})
    if not result:
        return None
    total = len(profile['groups']) or 1
    matched = result['matched_terms']
    result.update(case_name=title, relevance_status='partial_reference',
                  comparison_limit='검색 일치 조건: ' + (' / '.join(matched) or '교통사고') + '; 일부만 일치하는 참고 판례입니다(' + str(len(matched)) + '/' + str(total) + '개 조건). 조건이 같은 대목에서 함께 확인되지는 않았고, 사고 경로·차량 역할·비율은 별도 비교가 필요합니다.')
    return result

def filter_display_cases(cases):
    accepted=[];rejected=[];seen=set()
    registered={case_identity(c):c for group in VERIFIED_CASES.values() for c in group}
    for original in cases:
        case=dict(original);identity=case_identity(case)
        if identity in seen:continue
        seen.add(identity)
        reason=None
        if not civil_fault_number(case.get('case_number')):
            reason='민사 과실 참고 목록에서 형사·행정·미지원 사건번호 제외'
        elif identity in registered and case.get('source')==registered[identity].get('source'):
            case=dict(registered[identity]);case['relevance_status']='registered_chart_reference'
        elif (case.get('relevance_status')!=CASE_RELEVANCE_VERSION or
              not all(case.get('relevance_checks',{}).get(k) for k in ('civil_case','claim_subject','vehicle_collision_context','location_and_mechanism'))):
            reason='이전 키워드 검색 결과의 민사 사고 관련성이 재검증되지 않음'
        if reason:
            rejected.append({'court':case.get('court'),'case_number':case.get('case_number'),'reason':reason})
        else:
            case['date']=case_date(case.get('date',''))
            accepted.append(case)
    return accepted,rejected

def sanitize_case_bundle(bundle):
    bundle=json.loads(json.dumps(bundle,ensure_ascii=False))
    out=bundle['rule_engine_output'];removed=[];merged=[];bytype={}
    root,excluded=filter_display_cases(out.get('related_cases',[]));removed.extend(excluded)
    for result in out.get('results',[]):
        cases,excluded=filter_display_cases(result.get('related_cases',[]));removed.extend(excluded)
        result['related_cases']=cases;merged.extend(cases)
        bytype.setdefault(str(result['accident_type']),[]).extend(cases)
        if result.get('case_lookup'):
            result['case_lookup']['count']=len(cases)
            result['case_lookup']['relevance_version']=CASE_RELEVANCE_VERSION
    merged.extend(root)
    out['related_cases']=filter_display_cases(merged)[0][:CASE_TARGET_COUNT]
    audits=[];seen=set()
    for old in out.get('case_lookup',[]):
        audit=dict(old);key=str(audit.get('accident_type'))
        if key in seen:continue
        seen.add(key)
        audit['count']=len(filter_display_cases(bytype.get(key,root))[0])
        audit['relevance_version']=CASE_RELEVANCE_VERSION
        if audit['count']<CASE_TARGET_COUNT:
            if audit.get('status') not in ('disabled','unavailable'):audit['status']='insufficient'
            audit['reason']='민사 배상·차량 충돌·장소·진행 조건을 검토한 참고 자료가 부족합니다. 무관한 판례로 개수를 채우지 않습니다.'
        audits.append(audit)
    out['case_lookup']=audits
    existing=out.get('case_validation',{}).get('excluded',[])
    unique={json.dumps(v,sort_keys=True,ensure_ascii=False):v for v in existing+removed}
    out['case_validation']={'version':CASE_RELEVANCE_VERSION,'excluded':list(unique.values()),
        'notice':'등록 도표의 판례 요약과 API 원문 검색 후보를 구분하며 실제 사고의 법적 적용 여부를 확정하지 않음'}
    return bundle
