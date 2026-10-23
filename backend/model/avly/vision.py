"""OpenAI 호출, 재시도, 응답 캐시. (모델 공급자를 바꿀 때 교체할 지점)"""
from .dataio import prompt_text
import hashlib
import json
import re
from openai import OpenAI
from .constants import ROLE, VERBOSE, VERSION
from .context import ctx
from .config import get_secret
from .schemas import FrameReferenceError, Observation, Scan
from .facts import normalize_tracks


def digest_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def strict_schema(model):
    value = model.model_json_schema()

    def visit(node):
        if isinstance(node, dict):
            if node.get('type') == 'object':
                node['additionalProperties'] = False
                node['required'] = list(node.get('properties', {}))
            for child in list(node.values()):
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
    visit(value)
    return value

def request_with_server_retry(stage, cache_key, **kwargs):
    import time
    from openai import APIStatusError
    for retry in range(3):
        try:
            return ctx.client.responses.create(**kwargs)
        except APIStatusError as exc:
            status = exc.status_code
            diagnostic = {'stage': stage, 'http_status': status, 'request_id': getattr(exc, 'request_id', None), 'request_attempt': retry + 1, 'error': 'API 서버 오류' if status >= 500 else 'API 요청 오류', 'usage': None, 'usage_note': '실패 응답의 토큰 사용량은 제공되지 않음; 0으로 확정하지 않음'}
            path = ctx.result_dir / f'api_error_{cache_key[:12]}_{retry + 1}.json'
            path.write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding='utf-8')
            ctx.stages.append({**diagnostic, 'model': kwargs.get('model'), 'cached': False})
            if status not in (500, 502, 503, 504) or retry == 2:
                raise RuntimeError(f'{stage}: API 오류 HTTP {status}. 진단: {path}') from exc
            delay = 3 * 2 ** retry
            headers = getattr(getattr(exc, 'response', None), 'headers', {})
            retry_after = headers.get('retry-after') if headers else None
            if retry_after:
                try:
                    server_delay = float(retry_after)
                except (ValueError, TypeError):
                    from email.utils import parsedate_to_datetime
                    from datetime import datetime, timezone
                    try:
                        server_delay = (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds()
                    except (ValueError, TypeError, OverflowError):
                        server_delay = 0
                delay = max(delay, server_delay)
            if delay > 60:
                raise RuntimeError(f'{stage}: 서버가 {delay:.0f}초 이후 재시도를 요청했습니다. 잠시 후 다시 실행하세요. 진단: {path}') from exc
            print(f'{stage}: 서버 오류 {status}, {delay:.0f}초 후 재시도 {retry + 1}/2')
            time.sleep(delay)

def call(stage, model, schema, content, output_limit, validator=None):
    signature = json.dumps([VERSION, ctx.video_hash, ctx.csv_hash, ROLE, model, output_limit, constrained_frame_schema(schema, content), content], ensure_ascii=False, sort_keys=True)
    key = hashlib.sha256(signature.encode()).hexdigest()
    path = ctx.cache_dir / f'{key}.json'
    if ctx.USE_CACHE and path.exists():
        try:
            saved = json.loads(path.read_text(encoding='utf-8'))
            parsed = schema.model_validate(saved['parsed'])
            if validator:
                validator(parsed)
        except (ValueError, KeyError) as exc:
            cache_diagnostic = {'stage': stage, 'cached': True, 'error': str(exc), 'cache_path': str(path)}
            if isinstance(exc, FrameReferenceError):
                cache_diagnostic.update(exc.diagnostic())
            (ctx.result_dir / f'cache_error_{key[:12]}.json').write_text(json.dumps(cache_diagnostic, ensure_ascii=False, indent=2), encoding='utf-8')
            print(stage, ': 기존 캐시 검증 실패, 새 응답을 요청합니다.')
        else:
            ctx.stages.append({'stage': stage, 'model': model, 'cached': True, 'usage': None, 'normalization': saved.get('normalization', [])})
            print(stage, ': 캐시 재사용 / 이번 호출 토큰 0')
            return parsed
    if ctx.client is None:
        ctx.client = OpenAI(api_key=get_secret('OPENAI_API_KEY', required=True), max_retries=0, timeout=180)
    correction = ''
    limit = output_limit
    for attempt in range(2):
        instructions = ROLE + '\n모든 설명은 짧게. 같은 상태는 구간 하나로 묶고 프레임별 문장을 반복하지 마라. 근거 ID는 핵심만 남기되 서로 다른 차량과 사고 전후 상태는 합치지 마라.'
        instructions += correction
        response = request_with_server_retry(stage, key, model=model, instructions=instructions, input=[{'role': 'user', 'content': content}], text={'format': {'type': 'json_schema', 'name': schema.__name__, 'strict': True, 'schema': constrained_frame_schema(schema, content)}}, max_output_tokens=limit)
        usage = {k: getattr(response.usage, k, 0) or 0 for k in ctx.meter} if response.usage else None
        if usage:
            for k in ctx.meter:
                ctx.meter[k] += usage[k]
        status = response.status
        reason = getattr(response.incomplete_details, 'reason', None)
        record = {'stage': stage, 'model': model, 'cached': False, 'usage': usage, 'attempt': attempt + 1, 'status': status, 'incomplete_reason': reason, 'max_output_tokens': limit}
        ctx.stages.append(record)
        print(stage, f'/ 시도 {attempt + 1}:', usage or '사용량 미제공')
        diagnostic_path = ctx.result_dir / f'response_error_{key[:12]}_{attempt + 1}.json'

        def fail(message):
            diagnostic_path.write_text(json.dumps({**record, 'error': message, 'output_text': response.output_text, 'current_run_usage': dict(ctx.meter)}, ensure_ascii=False, indent=2), encoding='utf-8')
            return RuntimeError(f'{stage}: {message}\n진단 저장: {diagnostic_path}')
        if status != 'completed':
            error = fail(f'응답 미완료: {status} / {reason}')
            if status == 'incomplete' and reason == 'max_output_tokens' and (attempt == 0):
                print('출력 한도에 도달: 한도를 늘려 한 번만 재시도합니다. 첫 호출 사용량도 합산합니다.')
                limit = min(output_limit * 2, 6000)
                continue
            raise error
        if any((getattr(part, 'type', None) == 'refusal' for item in response.output for part in getattr(item, 'content', []))):
            raise fail('모델이 응답을 거절했습니다. 자동 재시도하지 않습니다.')
        try:
            parsed = schema.model_validate_json(response.output_text)
            raw_identity = {'tracks': [t.model_dump() for t in parsed.tracks], 'b_vehicle_id': getattr(parsed, 'b_vehicle_id', None)} if isinstance(parsed, (Scan, Observation)) else None
            notes = normalize_tracks(parsed) if isinstance(parsed, (Scan, Observation)) else []
            record['normalization'] = notes
            if notes:
                record['raw_identity'] = raw_identity
                if VERBOSE:
                    print('[차량 ID 정리]', notes)
            if validator:
                validator(parsed)
        except FrameReferenceError as exc:
            record['frame_reference_error'] = exc.diagnostic()
            error = fail(f'응답 검증 실패: {exc}')
            if attempt == 0:
                correction = prompt_text('frame_ref_correction') + json.dumps(exc.diagnostic(), ensure_ascii=False)
                print('프레임 인용 검증 실패: 허용 ID를 명시해 한 번만 재요청합니다. 사용량은 합산합니다.')
                continue
            raise error from exc
        except ValueError as exc:
            raise fail(f'응답 검증 실패: {exc}') from exc
        if ctx.USE_CACHE:
            path.write_text(json.dumps({'parsed': parsed.model_dump(), 'usage': usage, 'normalization': notes}, ensure_ascii=False), encoding='utf-8')
        return parsed

def constrained_frame_schema(model, content):
    schema = strict_schema(model)
    allowed = sorted(set((m.group(1) for part in content if part.get('type') == 'input_text' for m in [re.match('^(frame_\\d+) / ', part.get('text', ''))] if m)))
    if not allowed:
        return schema

    def string_enum(node):
        if node.get('type') == 'string':
            node.clear()
            node['$ref'] = '#/$defs/ProvidedFrameId'
        for child in node.get('anyOf', []):
            string_enum(child)

    def walk(node):
        if not isinstance(node, dict):
            return
        for key, value in node.get('properties', {}).items():
            if key.endswith('frame_id'):
                string_enum(value)
            elif key.endswith('frame_ids'):
                string_enum(value.get('items', {}))
        for child in node.values():
            if isinstance(child, dict):
                walk(child)
            elif isinstance(child, list):
                for x in child:
                    walk(x)
    walk(schema)
    schema.setdefault('$defs', {})['ProvidedFrameId'] = {'type': 'string', 'enum': allowed}
    return schema
