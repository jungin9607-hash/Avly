# Avly API 명세 (v0.4, 구현 기준)

실제로 구현된 API입니다. 서버가 만드는 Swagger(`http://localhost:8000/docs`)와 함께 보세요.
이전 초안(v0.3, v0.4)은 이 문서로 대체되어 삭제했습니다. 초안과 달라진 점은 맨 아래에 있습니다. (git 기록에서 볼 수 있습니다.)

## 기본 규칙

| 항목 | 규칙 |
| --- | --- |
| Base URL | `http://localhost:8000` (개발). 경로는 `/api/v1/...` (상태 확인만 `/health`) |
| 형식 | JSON. 영상 업로드만 `multipart/form-data` |
| 필드명, 식별자, 시간 | `snake_case`, UUID 문자열, UTC ISO 8601 |
| **소유 확인** | 사고를 만들 때 받은 `session_id`를 이후 요청의 **`X-Session-Id` 헤더**로 보낸다. 없으면 `401`, 남의 사고·분석은 **`404`**(있는지 알려 주지 않는다) |
| CORS | `CORS_ORIGINS`(기본 `http://localhost:5173`)에서 `X-Session-Id` 헤더를 포함해 허용 |
| 오류 형식 | `{"error": {"code": "...", "message": "..."}}`. 화면 분기는 `code`로 하고 `message`는 사용자에게 보여줄 수 있는 한국어 문구 |

## 흐름

```
POST /accidents (동의, session_id 받기)
→ POST /accidents/{id}/videos (영상 1개)
→ POST /accidents/{id}/analyses (분석 시작, 202)
→ GET  /analyses/{id} 를 반복 조회 ──────────────→ status: queued → processing(stage) → awaiting_confirmation
→ (사용자) 사고 상황 확인: situation 과 GET /catalog/accident-types 로 장소 → 유형 → 내 차 → 상대 차 고르기
→ GET  /analyses/{id}/adjustment-questions?accident_type_id=&role=   (가감요소 질문)
→ POST /analyses/{id}/confirm (확정한 유형과 답변, 202)
→ GET  /analyses/{id} 를 반복 조회 ──────────────→ status: processing(finalize) → completed (result)
```

분석이 끝나지 않고 끝나는 경우: `unsupported`(차대차가 아닌 사고), `failed`(오류).

## 분석 상태 `status`와 진행 단계 `stage`

| status | 뜻 | 화면 |
| --- | --- | --- |
| `queued` | 대기 중 | 진행 화면 |
| `processing` | 처리 중. `stage` 참고 | 진행 화면 (단계 표시) |
| `awaiting_confirmation` | 분석이 끝나 사용자 확인을 기다림. `situation` 있음 | 사고 상황 확인 화면 |
| `completed` | 결과 있음. `result` 참고 | 결과 화면 |
| `unsupported` | 차대차가 아닌 사고. `unsupported_reason` 있음. **오류가 아님** | 지원하지 않는 사고 안내 |
| `failed` | 실패. `error` 있음 | 오류 안내 |

`processing`일 때 `stage`는 `{id, index, total, label}`이고 `total`은 5입니다.

| `stage.id` | `index` | 내용 |
| --- | --- | --- |
| `plate_masking` | 1 | 번호판·사람 비식별화 |
| `overview` | 2 | 전체 흐름 분석 |
| `detail_review` | 3 | 사고 전후 상세 확인 (필요할 때만 실행되어 건너뛸 수 있음) |
| `case_matching` | 4 | 과실 유형 비교 |
| `finalize` | 5 | 결과 정리 (사용자 확인 뒤) |

사고(`accident.status`)는 `uploaded`, `analyzing`, `completed`, `failed`, `unsupported`입니다.

## 엔드포인트

| 메서드 | 경로 | 설명 | 성공 |
| --- | --- | --- | --- |
| GET | `/health`, `/health/db` | 서버, DB 상태 | 200 |
| GET | `/api/v1/catalog/accident-types` | 과실표 선택지 전체 (세션 불필요) | 200 |
| POST | `/api/v1/accidents` | 사고 생성과 동의 기록, 세션 발급 | 201 |
| GET | `/api/v1/accidents/{id}` | 사고 조회 | 200 |
| POST | `/api/v1/accidents/{id}/videos` | 영상 업로드 (사고마다 하나) | 201 |
| GET | `/api/v1/accidents/{id}/video-url` | 비식별 영상 재생 주소 | 200 |
| POST | `/api/v1/accidents/{id}/analyses` | 분석 시작 | 202 |
| GET | `/api/v1/analyses/{id}` | 분석 상태와 결과 | 200 |
| GET | `/api/v1/analyses/{id}/adjustment-questions` | 고른 유형의 가감요소 질문 | 200 |
| POST | `/api/v1/analyses/{id}/confirm` | 사용자가 확정한 내용으로 결과 계산 | 202 |
| GET | `/api/v1/media/{token}` | 서명된 주소로 영상 재생 (Range 지원) | 200/206 |
| POST | `/api/v1/analyses/{id}/reports` | 서버 PDF (미구현) | 501 |

### POST /api/v1/accidents

```json
{ "title": "퇴근길 차선 변경 사고", "consent": { "version": "2026-10-19", "analysis": true, "retention": false } }
```

| 필드 | 필수 | 설명 |
| --- | --- | --- |
| `title` | ✅ | 1~200자 |
| `consent.version` | ✅ | 사용자가 본 동의 문서 버전 |
| `consent.analysis` | ✅ | **`true`여야 한다.** 아니면 `422 CONSENT_REQUIRED` |
| `consent.retention` | | 영상 저장·추가 활용 동의 (선택). `false`면 세션이 끝날 때 영상을 삭제한다 |

**응답 201**: `id`, `title`, `status`, `created_at`, `expires_at`(세션 만료 시각), **`session_id`**

### POST /api/v1/accidents/{id}/videos

`file` 필드로 영상을 올린다. 사고마다 **하나만** 가능하다.
오류: `400 EMPTY_FILE`, `409 VIDEO_ALREADY_UPLOADED`, `413 FILE_TOO_LARGE`(기본 200MB), `415 UNSUPPORTED_FILE_TYPE`(기본 mp4, mov, avi)
응답은 영상 `id`, `accident_id`, `size_bytes`, `created_at`이고 **영상 주소는 없다**.

### GET /api/v1/accidents/{id}/video-url

`{"available": true, "url": "/api/v1/media/...", "expires_at": "..."}`. 번호판·사람을 가린 영상만 제공하고 **원본은 어떤 경우에도 제공하지 않는다**.
`available: false`이면 영상을 보관하지 않았거나(저장 동의 없음) 삭제된 것이다. 주소는 짧게(기본 10분) 유효하므로 화면에 들어올 때 받는다.
`<video src>`는 헤더를 보낼 수 없어서 이 주소에 서명이 들어 있다. 앞에 서버 주소를 붙여 쓴다.

### POST /api/v1/accidents/{id}/analyses

바로 202로 `{analysis_id, status, status_url}`를 돌려준다. 오류: `409 VIDEO_REQUIRED`, `409 ANALYSIS_IN_PROGRESS`(사고마다 진행 중인 분석은 하나).

### GET /api/v1/analyses/{id}

```json
{
  "analysis_id": "…", "accident_id": "…",
  "status": "awaiting_confirmation",
  "stage": null,
  "situation": { "…": "아래 참고" },
  "result": null,
  "unsupported_reason": null,
  "error": null,
  "created_at": "…", "updated_at": "…"
}
```

`situation`은 `awaiting_confirmation` 이후로 계속 들어 있다.

| 필드 | 설명 |
| --- | --- |
| `summary`, `road_shape`, `my_action`, `other_action` | AI 가 본 사고 상황 |
| `contact` | 접촉 확실도 (`접촉 관찰`, `충돌 정황 강함`, `접촉 추정`, `근접만 관찰`, `판단 불가`) |
| `needs_check` | 사용자가 확인해야 할 점 (문장 목록) |
| `candidates[]` | 과실표 후보. `accident_type_id`, `role`, `place`, `feature`, `my_progress`, `other_progress`, `base_me`, `base_other`, `source`(`matched` 확실한 후보 / `reference` 참고용), `eligible` |
| `default_index` | 미리 골라 둘 후보의 위치. **`null`이면 AI 가 확신하지 못한 것**이니 미리 고르지 않는다 |

`role`은 **내 차가 과실표에서 맡은 쪽**(`A` 또는 `B`)이다. 같은 유형이라도 내 차가 A인지 B인지에 따라 내 과실과 진행 이름이 바뀐다.
`error.code`: `VIDEO_TOO_LONG`(영상이 20초 초과), `AI_NOT_CONFIGURED`(AI 키 없음 등 서비스 준비 안 됨), `ANALYSIS_FAILED`, `FINALIZE_FAILED`.

### GET /api/v1/catalog/accident-types

`{"count": 261, "items": [ {accident_type_id, role, place, feature, my_progress, other_progress, base_me, base_other} ]}`.
화면의 네 항목(장소, 사고 유형, 내 차의 움직임, 상대 차의 움직임)이 같은 것은 하나로 합쳐 두었으므로 **네 항목을 고르면 선택지가 하나로 정해진다.**
프론트는 이 목록으로 앞 항목을 고를 때마다 뒤 항목의 보기를 좁힌다.

### GET /api/v1/analyses/{id}/adjustment-questions?accident_type_id=11&role=A

고른 유형에 등록된 가감요소를 쉬운 말 질문으로 돌려준다. 등록되지 않은 유형은 `registered: false`, `questions: []`이고 기본 비율만 안내한다(**133개 유형 중 7개만 등록**).

```json
{ "accident_type_id": 11, "role": "A", "registered": true, "questions": [ {
  "key": "other.signal_delay", "factor": "signal_delay", "who": "상대 차", "group": "B_signal",
  "title": "방향지시등을 켜지 않았거나 너무 늦게 켰어요", "easy": "차선을 바꾸기 전에 …",
  "question": "상대 차가 방향지시등을 켜지 않았거나, 차선을 바꾸는 순간에야 켰나요?",
  "effect": "상대 차 과실 +10%p", "delta_pp": 10, "needs_user": false,
  "options": ["예", "아니요", "잘 모르겠어요"],
  "suggested": { "answer": "예", "basis": "영상에서 관찰", "evidence": "방향지시등이 켜지지 않은 장면" },
  "reviewed": false } ] }
```

- **`예`라고 답하면 그 가감요소가 적용되도록** 질문을 썼다. `key`는 `me.`(내 차) 또는 `other.`(상대 차)로 시작한다.
- `suggested`는 영상에서 관찰·추정한 것이 있을 때만 있다 (사용자가 답하기 전의 AI 제안). 사용자의 답이 항상 우선한다.
- `needs_user`: 영상만으로는 알 수 없는 항목 (예: 현저한 과실). 항상 사용자에게 묻는다.
- `reviewed: false`는 쉬운 말 문장을 아직 사람이 검수하지 않았다는 뜻이다.

### POST /api/v1/analyses/{id}/confirm

```json
{ "accident_type_id": 11, "role": "A", "answers": [ { "key": "other.signal_delay", "answer": "예" } ] }
```

- 맞는 유형이 없으면 `"accident_type_id": null`, `role`과 `answers`는 비운다. 결과는 `state: "unresolved"`(비율 없음)로 나온다.
- 답하지 않은 질문은 `잘 모르겠어요`로 보내면 된다. 서버는 이를 0으로 확정하지 않고 **미확인**으로 둔다.
- 응답은 `status: processing`, `stage.id: finalize`인 분석이다. 이어서 `GET /analyses/{id}`를 조회해 `completed`를 기다린다.
- 오류: `409 ANALYSIS_NOT_AWAITING`, `404 ACCIDENT_TYPE_NOT_FOUND`, `422 ROLE_REQUIRED`, `422 INVALID_ANSWER`(이 유형에서 묻지 않는 항목이나 같은 항목이 두 번 들어 있음)

## 결과 `result`

`status`가 `completed`일 때 들어 있다.

| 필드 | 설명 |
| --- | --- |
| `state` | `final`(최종 비율 있음), `partial`(미확인 요소가 있어 확인된 것만 반영), `base_only`(가감요소 미등록이라 기본 비율만), `unresolved`(유형 확정 불가, 비율 없음) |
| `summary`, `situation` | 사고 상황 설명 (`road_shape`, `my_action`, `other_action`, `contact`) |
| `accident_type` | 확정한 유형 (`accident_type_id`, `role`, `place`, `feature`, `my_progress`, `other_progress`). `unresolved`면 `null` |
| `fault` | `base`(기본), `adjusted`(반영한 값, `partial`도 있음), `final`(`final` 상태일 때만 값), `bounds_applied`. 각각 `{me, other}`. `unresolved`면 `null` |
| `steps[]` | 화면의 단계 카드: `kind`(`base`/`adjustment`), `title`, `easy`, `effect`, `who`, `factor`, `delta_pp`, **그 단계까지 반영한 `me`, `other`** |
| `adjustments` | `registered`, `applied[]`, `not_applied[]`(이유 포함), `pending[]`(확인하지 못한 요소, `question` 포함) |
| `laws[]` | 관련 도로교통법 조문: `article`, `label`, `name`, `easy`, `missing`(풀이를 아직 안 썼으면 true) |
| `explanation` | `base`, `situation`, `status` (쉬운 말 문장, **AI 가 아니라 미리 쓴 문장**) |
| `timeline[]` | 구간: `kind`, `actor`(`me`/`other`/`both`), `start_sec`, `end_sec`(**영상 시작 기준 초**), `description`, `certainty`, `evidence_text` |
| `impact` | `{sec, contact, confirmed}`. **`confirmed`가 true일 때만** 충돌 시점을 기준으로 말한다 |
| `related_cases[]` | 판례: `case_id`, `court`, `date`, `case_number`, `summary`, `comparison_limit`, `source_url`, `source_kind`, `source_label`, `verified`, `relevance_status`, `comparison` |
| `related_cases[].comparison` | `match_level`(`same_type`/`partial`), `match_label`, `common[]`, `differences[]`, `note`. **퍼센트는 없다** |
| `reference_candidates[]` | 분석 단계의 과실표 후보 (`unresolved`일 때 참고용으로 보여 준다) |
| `notice` | 법적 효력이 없다는 고지 문구 |

**보여주지 않는 값:** 속도, G값, 감속, 차간거리, 방향지시등 확률, 충돌 시각의 확정, 판례 유사도 퍼센트는 서버가 만들지 않는다.

예시 응답: [frontend/src/api/fixtures/](../frontend/src/api/fixtures/) (`result_final.json`, `result_partial.json`, `result_base_only.json`, `result_unresolved.json` 등. 실제 서버 코드가 만든 값)

## 오류 코드

| 상태 | code | 상황 |
| --- | --- | --- |
| 400 | `EMPTY_FILE` | 0바이트 파일 |
| 401 | `SESSION_REQUIRED`, `SESSION_INVALID` | `X-Session-Id`가 없거나 형식이 틀림 |
| 403 | `MEDIA_LINK_INVALID` | 영상 주소가 틀리거나 만료됨 |
| 404 | `ACCIDENT_NOT_FOUND`, `ANALYSIS_NOT_FOUND` | 없거나 **남의 것** |
| 404 | `ACCIDENT_TYPE_NOT_FOUND`, `VIDEO_NOT_AVAILABLE`, `NOT_FOUND` | 과실표에 없는 유형, 재생할 영상 없음, 없는 경로 |
| 405 | `METHOD_NOT_ALLOWED` | |
| 409 | `VIDEO_ALREADY_UPLOADED`, `VIDEO_REQUIRED`, `ANALYSIS_IN_PROGRESS` | 영상 규칙, 진행 중인 분석 |
| 409 | `ANALYSIS_NOT_AWAITING`, `ANALYSIS_NOT_COMPLETED` | 확인 대기가 아닐 때 `confirm`, 완료 전 `reports` |
| 413 | `FILE_TOO_LARGE` | 업로드 용량 초과 |
| 415 | `UNSUPPORTED_FILE_TYPE` | 허용하지 않는 확장자 |
| 422 | `CONSENT_REQUIRED`, `ROLE_REQUIRED`, `INVALID_ANSWER`, `VALIDATION_ERROR` | 동의 없음, 역할 누락, 잘못된 답변, 요청 형식 오류(`details` 포함) |
| 500 / 501 / 503 | `INTERNAL_SERVER_ERROR` / `REPORT_NOT_IMPLEMENTED` / `DATABASE_UNAVAILABLE` | |

## 개발·테스트

worker 가 `ENGINE=fake`(기본 개발 설정)이면 영상 파일 **첫 줄**의 지시로 상황을 만들 수 있다. 실제 영상이 아니어도 된다.

| 첫 줄 | 결과 |
| --- | --- |
| (지시 없음) | 정상 분석 (직선 도로 진로변경 사고, 유형 11 후보) |
| `FAKE unsupported 차대보행자` | `unsupported` |
| `FAKE too_long 55` | `failed`, `VIDEO_TOO_LONG` |
| `FAKE fail` | `failed`, `ANALYSIS_FAILED` |
| `FAKE fixture parking` | 주차장 사고: 참고 후보만 있고 미리 고르지 않음 |

확인 스크립트: [backend/tests/e2e_smoke.py](../backend/tests/e2e_smoke.py) (HTTP), [frontend/e2e/](../frontend/e2e/README.md) (브라우저)

## 초안(v0.4 draft)과 달라진 점

| 초안 | 구현 |
| --- | --- |
| 사전 설문(`/survey`) | **없음.** 영상에서 알 수 있는 것은 AI 가 먼저 파악하고 사용자가 확인한다 |
| `POST /analyses/{id}/answers`, `follow_up_questions` | **없음.** 유형을 확정하면 `adjustment-questions`로 질문을 받는다 |
| `confirm`(상황 확인만) | `confirm` 한 번에 유형, 역할, 가감요소 답변을 보낸다 |
| `fault_options[]` | 확정한 유형 하나의 `fault` + `steps[]` (유형을 사용자가 확정하므로 후보가 여러 개일 필요가 없다) |
| `stage.total` 4 | 5 (`finalize` 추가) |
| 결과의 `report_text` | 없음 (PDF는 브라우저 인쇄) |
