"""텍스트만 보내는 LLM 호출 (이미지 없음). 판례 비교처럼 이미지가 필요 없는 곳에서 쓴다.

모델 공급자를 바꿀 때 vision.py 와 함께 교체할 지점이다. 응답은 JSON 스키마(strict)로 받아 pydantic 으로 검증한다.
"""
import time

from .config import get_secret


class LLMError(RuntimeError):
    pass


def ask_json(model, instructions, text, schema, max_output_tokens=1800, client=None):
    """instructions 와 text 를 보내 schema(pydantic 클래스)에 맞는 객체를 돌려준다. (객체, 사용량 dict) 반환.

    서버 오류(5xx, 시간 초과)는 두 번까지 다시 시도한다. 거절·미완료·형식 오류는 LLMError 로 올린다.
    """
    from .vision import strict_schema
    if client is None:
        from openai import OpenAI
        client = OpenAI(api_key=get_secret('OPENAI_API_KEY', required=True), max_retries=0, timeout=60)
    request = dict(model=model, instructions=instructions, input=[{'role': 'user', 'content': [{'type': 'input_text', 'text': text}]}],
                   text={'format': {'type': 'json_schema', 'name': schema.__name__, 'strict': True, 'schema': strict_schema(schema)}},
                   max_output_tokens=max_output_tokens)
    response = None
    for attempt in range(3):
        try:
            response = client.responses.create(**request)
            break
        except Exception as exc:   # 상태 코드가 5xx 이거나 연결 문제일 때만 다시 시도한다
            status = getattr(exc, 'status_code', None)
            retriable = status in (500, 502, 503, 504) or exc.__class__.__name__ in ('APITimeoutError', 'APIConnectionError')
            if not retriable or attempt == 2:
                raise LLMError('LLM 호출 실패: ' + exc.__class__.__name__ + (f' HTTP {status}' if status else '')) from exc
            time.sleep(2 * 2 ** attempt)
    if response.status != 'completed':
        raise LLMError('LLM 응답 미완료: ' + str(response.status))
    if any(getattr(part, 'type', None) == 'refusal' for item in response.output for part in getattr(item, 'content', [])):
        raise LLMError('LLM 이 응답을 거절했습니다.')
    try:
        parsed = schema.model_validate_json(response.output_text)
    except ValueError as exc:
        raise LLMError('LLM 응답 형식 오류') from exc
    usage = {k: getattr(response.usage, k, 0) or 0 for k in ('input_tokens', 'output_tokens')} if response.usage else {}
    return parsed, usage
