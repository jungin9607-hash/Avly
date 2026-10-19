# Avly API 명세 v0.4 (초안) — 실제 분석 모델 연결

> 📝 **초안입니다.** [v0.3](api.md)은 Mock 분석을 기준으로 만들었습니다.
> 이 문서는 `backend/model/Avly.py`(실제 분석 파이프라인)와 현재 프론트 화면 흐름에 맞춰 **바뀌는 부분만** 정리했습니다.
> 바뀌지 않는 부분(공통 규칙, 오류 형식, 사고 생성, 영상 업로드)은 v0.3을 그대로 따릅니다.
> 의견은 [맨 아래 합의 항목](#합의가-필요한-항목)에 남겨 주세요.
>
> 🚗 **서비스는 차대차 사고만 지원합니다.** 보행자, 이륜차, 자전거 사고는 분석하지 않고 `unsupported` 상태로 안내합니다. ([4. 상태값](#4-상태값) 참고)

## 1. 왜 바꾸나

| | v0.3 (Mock) | 실제 모델 / 프론트 |
| --- | --- | --- |
| 분석 단계 | 한 번에 끝남 | 3단계(전체 흐름 → 사고 전후 상세 → CSV 유형 비교). 분 단위로 걸릴 수 있음 |
| 설문 | 분석 전에 한 번 | 프론트: 분석 전 고정 질문 2묶음. 모델: 분석 후 **영상 내용에 따라** 추가 질문 생성 |
| 사용자 확인 | 없음 | 프론트에 "AI가 분석한 사고 상황이 맞나요?" 단계가 있음 |
| 결과 | `fault_me`, `fault_other` 하나 | 후보가 여러 개이고, 기본 과실 + 가감 요소 구조. 확정 못 하면 `null` |
| 신뢰도 | `confidence` 숫자 | 모델이 "정확도·확률 점수 아님"이라고 명시하며 점수를 만들지 않음 |

## 2. 사용자 흐름

```
사고 생성 → 영상 업로드 → 사전 설문 → 분석 시작 → (polling) → 사고 상황 확인 ─┬→ 맞아요 → 결과
POST        POST          POST         POST         GET        GET            │
/accidents  /videos       /survey      /analyses    반복       status=         └→ 아니요 → 추가 질문 답변 → 다시 확인
                                                              awaiting_       POST /answers
                                                              confirmation
```

프론트 화면과의 대응은 이렇습니다.

| 프론트 단계 | API |
| --- | --- |
| 영상 선택, 수집 동의 | `POST /accidents`, `POST /accidents/{id}/videos` |
| 질문 1, 질문 2 | `POST /accidents/{id}/survey` (사전 설문) |
| 분석 중 | `POST /accidents/{id}/analyses` 후 `GET /analyses/{id}` polling |
| 사고 상황 확인 | `status = awaiting_confirmation`일 때의 `situation` 표시 |
| "맞아요, 분석 결과 보기" | `POST /analyses/{id}/confirm` |
| "아니요, 다시 확인할게요" | `follow_up_questions`에 답변 → `POST /analyses/{id}/answers` |
| 결과 / 타임라인 / 판례 화면 | `GET /analyses/{id}`의 `result` |

## 3. 변경 요약

| 구분 | 내용 |
| --- | --- |
| 상태값 추가 | `awaiting_confirmation` (사용자 확인 대기), `unsupported` (지원하지 않는 사고 유형) |
| 응답 필드 추가 | `stage`, `situation`, `follow_up_questions`, `unsupported_reason` |
| 엔드포인트 추가 | `POST /analyses/{id}/answers`, `POST /analyses/{id}/confirm` |
| 요청 변경 | 사고 생성에 동의 정보 추가, 사전 설문 항목에 `key` 추가 |
| 결과 형식 변경 | `fault_me`/`fault_other` → `fault_options[]`, `timeline`, `related_cases` 확장 |
| 삭제 | `confidence` (모델이 만들지 않음) |
| 유지 | 공통 규칙, 오류 형식, 사고 생성·조회, 영상 업로드 |

## 4. 상태값

분석 상태(`status`)는 다음 순서로 바뀝니다.

```
queued → processing → awaiting_confirmation → completed
              │
              ├──────→ unsupported   (차대차가 아닌 사고)
              └──────→ failed
```

| 값 | 뜻 | 프론트 동작 |
| --- | --- | --- |
| `queued` | 대기 중 | 진행 화면 |
| `processing` | 분석 중. `stage` 참고 | 진행 화면 (단계 표시) |
| `awaiting_confirmation` | 1차 분석 끝. 사용자 확인 대기 | "사고 상황 확인" 화면 |
| `completed` | 사용자가 확인함. 결과 사용 가능 | 결과 화면 |
| `unsupported` | **차대차가 아닌 사고**(보행자, 이륜차, 자전거)로 판단됨. 이후 분석을 하지 않음. `unsupported_reason` 참고 | "지원하지 않는 사고 유형" 안내 |
| `failed` | 실패. `error` 참고 | 오류 안내 |

사고(`accident.status`)는 기존 4가지(`uploaded`, `analyzing`, `completed`, `failed`)에 `unsupported`를 더한 5가지입니다.
`awaiting_confirmation`일 때 사고는 `analyzing`으로 둡니다. 분석이 `unsupported`로 끝나면 사고도 `unsupported`가 됩니다.

## 5. 엔드포인트

### POST /api/v1/accidents — 사고 생성 (변경)

수집 동의 정보를 함께 받습니다. **분석 동의는 필수**이고, **영상 저장·추가 활용 동의는 선택**입니다.

**요청**
```json
{
  "title": "퇴근길 차선 변경 사고",
  "consent": { "version": "2026-10-19", "analysis": true, "retention": false }
}
```

| 필드 | 필수 | 설명 |
| --- | --- | --- |
| `consent.version` | ✅ | 사용자가 본 동의 문서의 버전 |
| `consent.analysis` | ✅ | **`true`여야 합니다.** 아니면 `422 CONSENT_REQUIRED` |
| `consent.retention` | | 영상 저장·추가 활용 동의. `true`일 때만 영상을 보관하고, 아니면 세션이 끝날 때 영상을 삭제합니다 |

**응답 201**에는 `session_id`가 추가됩니다. 이후 모든 요청에 이 값을 함께 보내야 합니다 (헤더 이름은 [합의 항목](#합의가-필요한-항목)에서 정합니다).

### POST /api/v1/accidents/{accident_id}/videos — 영상 업로드 (변경 없음, 규칙만 추가)

- 영상은 **사고마다 하나만** 올릴 수 있습니다. 이미 있으면 `409 VIDEO_ALREADY_UPLOADED`입니다. (v0.3 백엔드에 이미 반영됨)
- 영상 길이는 **사고 전후 15초 내외(최대 20초)**입니다. 길이는 번호판 비식별화나 분석 시작 때 확인하므로, 초과하면 분석이 `failed`(`error.code = VIDEO_TOO_LONG`)로 끝납니다.

### POST /api/v1/accidents/{accident_id}/survey — 사전 설문 (변경)

요청 항목에 `key`를 추가합니다. 서버가 `key`로 모델의 입력 값과 연결하기 위해서입니다.

```json
{
  "answers": [
    { "key": "vehicle_condition", "question": "사고 당시 내 차의 컨디션은 어땠나요?", "answer": "이상 없음" },
    { "key": "signal", "question": "사고 직전 내 차량 진행 방향의 신호는 무엇이었나요?", "answer": "녹색" }
  ]
}
```

| 필드 | 필수 | 설명 |
| --- | --- | --- |
| `key` | ✅ | 질문 식별자. 아래 표 참고 |
| `question` | ✅ | 화면에 보여준 문구 (기록용) |
| `answer` | ✅ | 선택한 값. 모르면 `"모름"` |

현재 프론트의 질문과 `key` 후보는 다음과 같습니다. (모델 쪽 키와의 매핑은 [합의 항목 3번](#합의가-필요한-항목))

| key | 질문 | 모델 쪽 대응(예정) |
| --- | --- | --- |
| `vehicle_condition` | 내 차의 컨디션 | `a_vehicle_condition` |
| `driver_condition` | 운전자 상태 | 대응 없음 (기록용) |
| `speed` | 사고 직전 내 차 속도 | `a_speed_state` |
| `road_type` | 도로 형태 | `road_shape` |
| `road_surface` | 노면 상태 | `road_surface` |
| `visibility` | 시야 가림 | 대응 없음 (기록용) |
| `weather` | 날씨 | `weather` |
| `signal` | 내 차 진행 방향 신호 | `a_signal` |

### POST /api/v1/accidents/{accident_id}/analyses — 분석 시작 (유지)

동작은 v0.3과 같습니다. 202와 함께 `analysis_id`를 반환합니다. 1차 분석(3단계)이 시작됩니다.

### GET /api/v1/analyses/{analysis_id} — 상태·결과 조회 (변경)

#### 분석 중 (`processing`)

```json
{
  "analysis_id": "…",
  "accident_id": "…",
  "status": "processing",
  "stage": { "index": 3, "total": 4, "label": "사고 전후 상세 확인" },
  "is_mock": false,
  "situation": null,
  "follow_up_questions": [],
  "result": null,
  "error": null
}
```

| `stage.index` | `label` | 내용 |
| --- | --- | --- |
| 1 | 번호판 비식별화 | `plate_masking` (영상 전체를 한 장씩 처리하므로 시간이 걸림) |
| 2 | 전체 흐름 분석 | 모델의 `1/3 전체 흐름 분석`. 끝나면 사고 대상(차대차 여부)을 확인함 |
| 3 | 사고 전후 상세 확인 | 모델의 `2/3 사고 전후 상세 확인` (필요할 때만 실행됨. 건너뛰면 3을 지나 4로 감) |
| 4 | 과실 유형 비교 | 모델의 `3/3 CSV 연결·과실 시나리오` |

프론트의 가짜 진행률(타이머)은 `stage`로 교체합니다.

#### 지원하지 않는 사고 (`unsupported`)

영상 분석 2단계(또는 3단계) 직후 사고 대상이 보행자, 이륜차, 자전거로 **명확히** 판단되면 이후 AI 분석을 하지 않고 이 상태로 끝냅니다. 사고 대상이 불확실하면 차대차로 보고 계속 진행합니다.

```json
{
  "analysis_id": "…",
  "accident_id": "…",
  "status": "unsupported",
  "stage": null,
  "unsupported_reason": "차대보행자 사고는 지원하지 않습니다. 현재는 차대차 사고만 분석합니다.",
  "situation": null,
  "follow_up_questions": [],
  "result": null,
  "error": null
}
```

- `unsupported_reason`은 사용자에게 그대로 보여줄 수 있는 문구입니다. 사고 대상 이름(`차대보행자` 등)이 들어 있습니다.
- 이 상태는 **오류가 아닙니다.** `error`는 `null`이고 HTTP 응답도 200입니다.
- `/answers`, `/confirm`을 호출하면 `409 ANALYSIS_NOT_AWAITING`입니다.
- 번호판 비식별화와 1/3 분석은 이미 실행된 뒤이므로, 이 사고의 영상 보관 여부는 [합의 항목 7번](#합의가-필요한-항목)에서 정합니다.

#### 사용자 확인 대기 (`awaiting_confirmation`)

```json
{
  "analysis_id": "…",
  "status": "awaiting_confirmation",
  "stage": null,
  "situation": {
    "title": "주차장 통로와 주차구역에서 만난 사고",
    "summary": "흰색 세단이 전방 우측에서 좌측으로 횡단하다 내 차 앞에 가까이 접근했습니다.",
    "place": "주차장",
    "my_action": "미확인",
    "other_action": "횡단",
    "needs_check": ["접촉 시각은 프레임 기준으로 확정되지 않았습니다."]
  },
  "follow_up_questions": [
    {
      "key": "b_action",
      "group": "도로·진행 경로",
      "question": "가장 가까워지기 직전 상대 차는 어떻게 움직였나요?",
      "options": ["직진", "후진", "정지/대기", "주차 출차", "미확인"]
    }
  ],
  "result": null,
  "error": null
}
```

- `situation`은 프론트의 "AI가 분석한 사고 상황이 맞나요?" 화면에 그대로 표시합니다.
- `follow_up_questions`는 사용자가 **"아니요"**를 눌렀을 때 보여줄 질문입니다. 영상 내용에 따라 개수와 내용이 달라집니다. 서버가 주는 값을 그대로 그려야 하므로 프론트에 고정하면 안 됩니다.
- 모든 질문에는 `"미확인"` 보기가 있습니다.

#### 완료 (`completed`)

`result`가 채워집니다. 형식은 [6. 결과 형식](#6-결과-형식)을 참고하세요.

### POST /api/v1/analyses/{analysis_id}/answers — 추가 질문 답변 (신규)

사용자가 "아니요"를 누르고 추가 질문에 답했을 때 호출합니다. 서버가 답변을 반영해 후보와 과실을 다시 계산합니다.
영상 재분석 없이 규칙 계산만 다시 하므로(모델의 `survey_update_llm_tokens: 0`) **동기 처리하고 200으로 응답**합니다.

**요청**
```json
{
  "answers": [
    { "key": "b_action", "answer": "주차 출차" },
    { "key": "a_action", "answer": "직진" }
  ]
}
```

**응답 200**: `GET /analyses/{id}`와 같은 형식입니다. 대개 `awaiting_confirmation`이고, 갱신된 `situation`과 남은 `follow_up_questions`가 들어 있습니다.

| 상태 | code | 상황 |
| --- | --- | --- |
| 409 | `ANALYSIS_NOT_AWAITING` | `awaiting_confirmation`이 아닐 때 |
| 422 | `VALIDATION_ERROR` | 알 수 없는 `key`이거나 보기에 없는 `answer` |

### POST /api/v1/analyses/{analysis_id}/confirm — 사고 상황 확인 (신규)

사용자가 "맞아요, 분석 결과 보기"를 눌렀을 때 호출합니다. 상태가 `completed`로 바뀝니다.

**응답 200**: `status = completed`이고 `result`가 포함된 `GET /analyses/{id}` 형식입니다.

| 상태 | code | 상황 |
| --- | --- | --- |
| 409 | `ANALYSIS_NOT_AWAITING` | `awaiting_confirmation`이 아닐 때 |

### POST /api/v1/analyses/{analysis_id}/reports — PDF 리포트 (유지, 미구현 501)

모델이 텍스트 보고서(`report_text`)를 만들어 줍니다. PDF 변환은 아직 계획만 있습니다.

## 6. 결과 형식

`status = completed`일 때의 `result`입니다.

```json
{
  "summary": "…",
  "accident_type": {
    "title": "주차장 / 주차구역과 통로",
    "place": "주차장",
    "feature": "주차구역과 통로"
  },
  "fault_options": [
    {
      "accident_type_id": 126,
      "label": "탐색용 조건 비교 · 적용 유형 미확정",
      "is_reference_only": true,
      "my_progress": "통로 직진",
      "other_progress": "주차구역에서 직진 출차",
      "base_fault": { "me": 30, "other": 70 },
      "applied_adjustments": [],
      "available_adjustments": [
        { "label": "서행 불이행", "delta_pp": 10, "target": "me" }
      ],
      "final_fault": null,
      "unconfirmed_conditions": ["내 차가 주차장 통로를 주행했는지 확인 필요"],
      "source_url": "https://accident.knia.or.kr/…"
    }
  ],
  "timeline": [
    {
      "id": "…",
      "kind": "A 움직임",
      "actor": "me",
      "start_sec": 1.67,
      "end_sec": 7.67,
      "description": "…",
      "certainty": "판단 불가",
      "evidence_text": "…",
      "image_url": null
    }
  ],
  "related_cases": [
    {
      "court": "서울중앙지방법원",
      "date": "2015-12-18",
      "case_number": "2015나37411",
      "summary": "…",
      "comparison_limit": "후진 출차 사례이며 현재 영상과 같은 비율을 적용하지 않음",
      "source_url": "https://…",
      "source_kind": "손해보험협회 도표의 판례 요약; 판결문 원문 조회 아님",
      "relevance_status": "registered_chart_reference"
    }
  ],
  "report_text": "에블리 | 사고 분석 보고서 …",
  "notice": "…"
}
```

### v0.3과 달라진 점

| 항목 | v0.3 | v0.4 | 이유 |
| --- | --- | --- | --- |
| 과실비율 | `fault_me`, `fault_other` (합 100) | `fault_options[]`에 후보별로 `base_fault`, `final_fault` | 모델이 후보를 여러 개 내고, 조건이 확인되지 않으면 `final_fault: null` |
| 합계 100 검증 | 필수 | `final_fault`가 있을 때만 | 확정 못 하는 경우가 정상 동작임 |
| 신뢰도 | `confidence` | 삭제 | 모델이 점수를 만들지 않음 |
| 타임라인 시간 | `time_sec` (충돌 0초 기준, 음수) | `start_sec`, `end_sec` (영상 시작 기준) | 모델이 충돌 시각을 확정하지 않고 구간으로 기록함 |
| 판례 | 가상 데이터 (id, similarity) | 도표 판례 요약 (`court`, `case_number` 등) | 모델이 손해보험협회 도표와 법령 API로 찾음 |
| 이름 | `me` / `other` | `me` / `other` | 모델의 A(블랙박스 차량)=`me`, B(상대)=`other`로 변환 |

### 프론트 결과 화면과의 대응

| 프론트 화면 | 사용할 필드 |
| --- | --- |
| 과실 분석 결과 (`StepRatio`, `FinalRatio`) | `fault_options[].base_fault`, `final_fault` |
| 가감 요소 (`AdjustmentSteps`, `FactorCard`) | `applied_adjustments`, `available_adjustments` |
| 영상 증거 (`EvidenceCard`) | `timeline[].evidence_text`, `image_url` |
| 타임라인 (`/time`) | `timeline[]` |
| 판례 (`/law`) | `related_cases[]` |
| 분석 결과 저장 | `report_text` (PDF는 미구현) |

> ⚠️ 현재 프론트의 `reportContent.js`에는 "깜빡이 꺼짐 99.8%", "46km/h 준수" 같은 **모델이 만들지 않는 값**이 들어 있습니다(GPS, 방향지시등 픽셀 분석 등). 실제 연결 시 이 항목들은 모델이 제공하는 근거(`evidence_text`)로 바꾸거나 삭제해야 합니다.

## 7. 오류 코드 (추가)

| 상태 | code | 발생 상황 |
| --- | --- | --- |
| 409 | `ANALYSIS_NOT_AWAITING` | 확인 대기 상태가 아닌데 `/answers` 또는 `/confirm` 호출 |
| 409 | `ANALYSIS_NOT_COMPLETED` | 완료 전에 `result` 또는 리포트 요청 (기존) |
| 409 | `VIDEO_ALREADY_UPLOADED` | 이미 영상이 있는 사고에 다시 업로드 |
| 422 | `CONSENT_REQUIRED` | 분석 동의 없이 사고 생성 |
| — | `VIDEO_TOO_LONG` | 영상이 20초를 넘음. HTTP 오류가 아니라 **분석 상태 `failed`의 `error.code`**로 전달됨 |
| 502 | `AI_SERVICE_ERROR` | OpenAI 등 외부 API 호출 실패 (분석 `failed`의 `error.code`로도 사용) |

## 8. DB 변경 사항

[schema.sql](db/schema.sql)과 `repository.py`에 필요한 변경입니다.

| 대상 | 변경 | 이유 |
| --- | --- | --- |
| `analysis` | `status`, `stage` 저장 (현재는 메모리의 작업 상태에만 있음) | polling과 서버 재시작 대비 |
| `analysis` | `scene` JSONB 추가 (1차 분석의 중간 결과) | 사용자가 확인하는 동안 서버가 바뀌어도 이어서 계산해야 함 |
| `analysis` | `fault_me`, `fault_other`, `confidence` 삭제 또는 NULL 허용, `ck_analysis_fault_sum` 제거 | 확정 못 하는 경우를 표현해야 함 |
| `analysis` | `result` JSONB 추가 (`fault_options`, `related_cases`, `report_text`) | 모델 결과가 중첩 구조라 컬럼으로 나누기 부담이 큼 |
| `survey` | `key`, `kind`(`pre`/`follow_up`) 컬럼 추가 | 사전 설문과 모델이 만든 추가 질문을 구분 |
| `timeline` | `start_sec`, `end_sec`, `actor`, `kind`, `certainty`, `evidence_text` 추가, `time_sec` 대체 | 구간 기반 기록 |
| `legal_case` | 모델이 도표/API에서 찾은 판례를 쓰므로 **사용 여부 결정 필요** | [합의 항목 2번](#합의가-필요한-항목) |
| `video` | `duration` NOT NULL (schema.sql) ↔ 코드는 null 허용 | 현재 서로 어긋나 있음. 하나로 맞춰야 함 |

## 합의가 필요한 항목

1. **사용자 확인 단계를 API에 포함할지.**
   이 문서는 프론트의 "사고 상황 확인" 화면을 `awaiting_confirmation` + `/confirm`으로 반영했습니다. 화면을 없애면 `/confirm`과 이 상태는 필요 없어집니다.
2. **판례를 어디서 가져올지.**
   모델은 손해보험협회 도표(`fault_table.csv`)와 법령/판례 API로 판례를 찾습니다. 기존 DB 설계(`legal_case` + pgvector RAG)와 방식이 다릅니다. 하나를 정본으로 정해야 합니다.
3. **사전 설문 `key`와 모델 입력의 매핑.**
   프론트 질문(예: 도로 형태 6개 보기)과 모델 쪽 값(예: `road_shape`)의 선택지가 서로 다릅니다. 변환 표를 누가 정할지 합의가 필요합니다.
4. **타임라인 시간 기준.** 영상 시작 기준(`start_sec`)으로 바꿔도 되는지 프론트와 확인해야 합니다.
5. **결과 화면 문구.** "99.8%" 같은 수치 표현을 모델이 줄 수 있는 범위(근거 문장, 확실도 라벨)로 바꿔야 합니다.
6. **분석 소요 시간과 업로드 용량.** 단계마다 OpenAI를 호출하므로 영상 길이에 따라 오래 걸립니다. 영상 길이 상한과 타임아웃 기준이 필요합니다.
7. **지원하지 않는 사고(`unsupported`)의 처리.** 화면 문구(프론트에 `unsupported` 단계가 이미 있음), 이미 올라간 영상을 바로 삭제할지, 이용자에게 대신 안내할 방법(예: 보험사 상담)이 있는지.
8. **사고 대상 판단이 틀렸을 때.** 모델이 차대차를 보행자로 잘못 판단하면 정상 사고를 거부하게 됩니다. 그래서 불확실하면 계속 진행하도록 했지만, 사용자가 "아니요, 차대차예요"로 다시 시도할 수 있게 할지 정해야 합니다.
9. **`session_id`를 어떻게 보낼지.** 헤더(`X-Session-Id`)로 보낼지, 쿠키로 보낼지. 쿠키는 공유 링크와 CORS 설정을 함께 정해야 합니다.
10. **영상 길이 확인 시점.** 지금은 분석 시작 때 확인하므로 사용자가 올린 뒤에야 알게 됩니다. 업로드 직후(번호판 처리 전)나 프론트에서 재생 메타데이터로 미리 막을지 정해야 합니다.
