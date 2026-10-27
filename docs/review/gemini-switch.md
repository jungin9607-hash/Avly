# Gemini 전환 범위

결론: **코드 전체를 바꿀 필요는 없다.** 바뀌는 곳은 "외부 AI를 부르는 부분"이고, 사고 분석 로직(프롬프트 흐름, 검증, 규칙 계산, 판례, API, 프론트)은 그대로다. 다만 한 줄 설정 변경으로 끝나지는 않는다.

## 바꿔야 하는 곳

| 위치 | 내용 | 규모 |
|---|---|---|
| `backend/model/avly/vision.py` | `OpenAI().responses.create()` 호출, 재시도, 오류 처리를 Gemini SDK(`google-genai`)로 교체. 이 파일이 공급자 경계다. | 가장 큼 (파일 하나) |
| `backend/model/avly/textllm.py` | 판례 비교용 텍스트 전용 호출(OpenAI Responses API + JSON 스키마). Gemini로 바꾸면 같이 교체. 판례 비교 프롬프트는 `backend/app/worker/ai_compare.py`에 있다 | 작음 (함수 하나) |
| `backend/model/avly/video.py` `image_content()` | 이미지 입력 형식이 OpenAI 전용(`input_text`, `input_image`, `detail: high/low`). Gemini 형식으로 변환. `detail` 옵션은 없어서 해상도 조절 방식이 달라진다. | 작음 (함수 하나) |
| `backend/model/avly/constants.py` | 모델 이름 `gpt-4.1`, `gpt-4.1-mini`를 Gemini 모델로 | 설정값 |
| `backend/model/avly/config.py` | `OPENAI_API_KEY` 대신 `GEMINI_API_KEY` | 작음 |
| `backend/requirements-worker.txt` | `openai` 대신(또는 함께) `google-genai` | 작음 |
| `backend/.env.example`, README | 키 이름, 안내 | 작음 |
| `backend/app/worker/engines.py`, `runner.py` | `OPENAI_API_KEY` 문자열로 설정 오류를 판별하는 부분 | 작음 |
| 동의 문구 | 외부 전송 대상을 OpenAI → Google로. 문구와 `CONSENT_VERSION` 변경 | 문구 |

## 바뀌지 않는 곳
- 파이프라인 순서와 프롬프트 파일(`prompts/`) — 내용은 유지하되 품질 확인용 조정이 필요할 수 있다.
- JSON 출력 검증(`schemas.py`), 프레임 인용 검증, 차량 ID 정리
- 규칙 기반 과실 계산, 판례 조회, 가감요소 질문
- DB, API, worker, 프론트

## 위험하거나 확인이 필요한 것
1. **구조화 출력**: 지금은 OpenAI의 strict JSON schema(`additionalProperties: false`, 모든 필드 required)에 맞춰 스키마를 만든다. Gemini의 `response_schema`는 지원하는 JSON schema 범위가 달라서 `strict_schema()`와 `constrained_frame_schema()`를 손봐야 할 수 있다.
2. **품질이 같다는 보장이 없다**: 프레임 번호 인용, 차량 구분, 신호·차선 판단은 모델마다 다르다. **라벨이 있는 평가 영상으로 두 모델을 비교한 뒤** 결정해야 한다. 그래서 평가 영상이 먼저 필요하다.
3. **토큰·비용 계산**: `ctx.meter`가 OpenAI 사용량 필드명(`input_tokens` 등)에 맞춰져 있다. Gemini는 필드명이 다르다.
4. **재시도·오류 코드**: `APIStatusError`, HTTP 상태 기준 재시도를 Gemini의 오류 타입에 맞게 다시 쓴다.
5. **캐시**: 응답 캐시 키에 모델 이름이 들어가 있어서 섞이지는 않는다.
6. **무료 키 불가**: 무료 티어는 입력이 학습에 쓰일 수 있고 한도가 낮다. 유료 키가 필요하다 (동의 문구와도 관련).

## 권장 방식
- `vision.py`를 공급자별로 나누지 말고, **`PROVIDER=openai|gemini` 설정으로 고르는 얇은 어댑터**를 두면 두 모델을 같은 영상으로 비교하기 쉽다. (모델 파일을 나누거나 고치는 작업이므로 시작하기 전에 방식을 다시 설명하고 허락을 받는다.)
- 순서: 평가 영상 준비 → OpenAI로 기준 결과 확보 → 어댑터 추가 → 같은 영상으로 비교 → 결정.
- 예상 작업량: 어댑터 구현과 스키마 맞추기 반나절~1일, 품질 비교와 프롬프트 조정은 영상 수에 따라 하루 이상.
