# DB 설계 v0.4 제안

> 📝 **초안입니다.** 기존 [schema.sql](schema.sql)(v0.3)은 그대로 두었고, 바뀐 안은 [schema-v0.4-draft.sql](schema-v0.4-draft.sql)에 있습니다.
> 합의 후 이 안으로 교체합니다. 바꾸고 싶은 부분은 [맨 아래 합의 항목](#합의가-필요한-항목)에 남겨 주세요.
>
> ✅ **초안 SQL은 PostgreSQL 17에서 실제로 실행해 확인했습니다.** 9개 테이블이 오류 없이 만들어지고, 제약조건 37개 시나리오(잘못된 값 거부, 정상 값 허용, 사고 삭제 시 연쇄 삭제)가 모두 의도대로 동작했습니다.

## 1. 설계에 반영한 결정

| 결정 | DB에 미치는 영향 |
| --- | --- |
| 서비스는 **차대차 사고만** 지원, 나머지는 지원하지 않음 | `status = 'unsupported'` 추가, 이유는 `analysis.unsupported_reason` |
| 번호판 비식별화가 분석보다 먼저 | 원본과 비식별본을 구분(`video.kind`), 분석에는 비식별본만 연결 |
| 원본 영상은 비식별이 잘못됐을 때를 대비해 **세션에 보관** | `accident.session_id`(소유 토큰), `expires_at`(만료), `video.deleted_at`(파일 삭제 기록) |
| **분석 동의는 필수**, **영상 저장·추가 활용 동의는 선택** | `accident.consent_at`(필수), `accident.retention_consent_at`(선택). 선택 동의가 없으면 세션 종료 시 영상 삭제 |
| **영상은 사고마다 하나만** | `video`에 원본 기준 부분 유니크 인덱스 `uq_video_original` |
| 영상은 사고 전후 15초 내외 | 길이 초과는 분석 실패 `VIDEO_TOO_LONG`(분석 시작 전에 확인) |
| 판례는 **DB에서 먼저 찾고, 없으면 API로 가져옴** | `legal_case`에 저장, `case_lookup`으로 조회 기록, 검수 여부 `verified` |
| 사용자가 사고 상황 4개 항목을 확인하고, 가감요소를 답함 | `analysis.confirmed`, `survey.kind` |
| 확정할 수 없는 과실은 NULL로 둠 | 과실 컬럼 NULL 허용 |
| GPT/Gemini를 비교하고 비용을 추적 | `analysis_stage_log` |

## 2. 저장 원칙

1. **조회·연결이 필요한 것은 테이블로, 화면에 보여주기만 하는 중첩 결과는 JSONB 한 곳(`analysis.result`)에 둡니다.**
   모델 결과 형식이 버전마다 바뀌므로, 컬럼으로 쪼개면 마이그레이션이 계속 생깁니다.
   목록 화면에 필요한 `fault_me`, `fault_other`, `accident_type_id`만 컬럼으로 꺼내 둡니다.
2. **과실표와 가감요소는 DB에 넣지 않고 저장소 파일로 관리합니다.** (`fault_table_car_to_car.csv`, `avly/data/adjustment_rules.json`)
   자주 바뀌지 않고, 숫자가 틀리면 과실비율이 틀리므로 변경 이력과 PR 리뷰가 필요합니다.
   DB의 `accident_type_id`는 그 CSV의 `accident_type` 값입니다.
3. **영상 같은 파일은 객체 저장소에 두고 DB에는 키만 저장합니다.** (`storage_key`는 URL이 아닙니다)
4. **사용자 데이터와 수집·갱신되는 데이터(판례)만 DB에 둡니다.**

## 3. 테이블 변경 요약

| 테이블 | v0.3 → v0.4 | 이유 |
| --- | --- | --- |
| `accident` | `session_id`, `consent_version`, `consent_at`, `expires_at` 추가. status에 `unsupported` | 소유자 구분, 수집 동의 기록, 세션 만료 |
| `video` | `kind`, `source_video_id`, `sha256`, `size_bytes`, `fps`, `width`, `height`, 비식별 통계 3개, `expires_at`, `deleted_at` 추가. `duration`을 NULL 허용. `video_url` → `storage_key` | 원본·비식별본 구분, 코드가 추출 전까지 `duration`을 null로 두는 것과 맞춤 |
| `analysis` | **상태와 결과를 한 행에 저장.** `status`, `stage`, `error_*`, `unsupported_reason`, `accident_type_id`, `scene`, `confirmed`, `result`, 재현 정보 3개, 시각 4개, `attempt`, `parent_analysis_id` 추가. `fault_*` NULL 허용, `confidence` 삭제 | 지금은 상태가 서버 메모리에만 있음, 확정 못 하는 경우 표현, 재분석 추적 |
| `survey` | `analysis_id`, `kind`, `key`, `group_name`, `options`, `answered_at` 추가 | 사전 질문, 모델이 만든 추가 질문, 가감 질문을 구분 |
| `analysis_stage_log` | **신규** | 단계별 모델, 토큰, 캐시 여부, 시간 기록 |
| `legal_case` | 임베딩 삭제. `court`, `decided_on`, `case_number`, `source_kind`, `verified*`, `raw`, `fetched_at` 추가. `(court, case_number)` 유일 | 유형 번호 기반 조회라 임베딩 불필요. 출처와 검수 상태 관리 |
| `case_accident_type` | **신규** (유형 ↔ 판례, N:M) | 같은 판례가 여러 유형에 쓰임 |
| `case_lookup` | **신규** | 판례가 없는 유형에서 API를 반복 호출하지 않기 위함 |
| `report` | `pdf_url` → `pdf_key` | 객체 키 |
| `timeline` | **삭제** → `analysis.result`에 포함 | 모델은 충돌 시점이 아닌 구간으로 기록하고, 화면 표시용이라 별도 테이블이 불필요 |
| `case_match` | **삭제** → `case_accident_type` 사용 | 코사인 유사도 대신 유형 번호로 연결 |
| pgvector 확장 | **삭제** | 의미 검색이 필요해지면 그때 추가 |

## 4. `analysis` 상태와 전이

```
queued → processing → awaiting_confirmation → completed
           │                  │
           ├→ unsupported     └→ (추가 질문 답변 후 다시 awaiting_confirmation)
           └→ failed
```

| `stage` (processing일 때) | 내용 |
| --- | --- |
| `plate_masking` | 번호판 비식별화 |
| `overview` | 1/3 전체 흐름 분석 |
| `detail_review` | 2/3 사고 전후 상세 확인 (필요할 때만) |
| `case_matching` | 3/3 과실표 유형 비교 |

- **`unsupported`**: 1단계 분석에서 차대차가 아닌 사고(보행자, 이륜차, 자전거)로 판단되면 이후 단계를 실행하지 않고 이 상태로 끝냅니다. AI 호출 비용도 아낄 수 있습니다.
- **사고당 진행 중인 분석은 하나**: `queued`, `processing`, `awaiting_confirmation` 상태는 사고마다 하나만 가질 수 있습니다. 부분 유니크 인덱스(`uq_analysis_active`)로 DB가 보장합니다. 기존에는 서버 메모리에서만 검사했습니다.
- **재분석**: 새 행을 만들고 `parent_analysis_id`로 이전 분석을 가리킵니다. 이전 결과는 그대로 남습니다.

## 5. `analysis.result` JSON 구조

[API 명세 v0.4](../api-v0.4-draft.md)의 `result`와 같은 형태입니다.

```json
{
  "summary": "…",
  "accident_type": { "title": "…", "place": "…", "feature": "…" },
  "fault_options": [
    {
      "accident_type_id": 126,
      "is_reference_only": true,
      "base_fault": { "me": 30, "other": 70 },
      "applied_adjustments": [],
      "available_adjustments": [{ "label": "서행 불이행", "delta_pp": 10, "target": "me" }],
      "final_fault": null,
      "unconfirmed_conditions": ["…"]
    }
  ],
  "timeline": [{ "kind": "A 움직임", "actor": "me", "start_sec": 1.67, "end_sec": 7.67, "certainty": "판단 불가", "evidence_text": "…", "image_key": null }],
  "related_cases": [{ "case_id": "…", "court": "…", "case_number": "…", "comparison_limit": "…", "verified": true }],
  "report_text": "…",
  "notice": "…"
}
```

- `related_cases`는 **조회 시점의 스냅샷**입니다. 나중에 판례 검수 상태가 바뀌어도 그때 사용자에게 보여준 내용을 확인할 수 있습니다. 최신 상태가 필요하면 `case_id`로 `legal_case`를 다시 조회합니다.
- `confirmed`에는 사용자가 확인한 `place`, `accident_type_id`, `a_process`, `b_process`를 저장합니다.

## 6. 판례 조회 흐름: DB 먼저, 없으면 API

```
유형 번호로 case_accident_type 조회
  ├─ 판례가 있음 → 그대로 사용 (verified 여부를 화면에 표시)
  └─ 없음 → case_lookup 확인
        ├─ retry_after 전 → API를 부르지 않고 "판례 없음"으로 응답
        └─ 그 외 → 법령 API 호출
              ├─ 성공 → legal_case 저장 (verified = false, raw 보관)
              │          + case_accident_type 연결 + case_lookup = found
              ├─ 결과 없음 → case_lookup = empty, retry_after 설정
              └─ API 오류 → case_lookup = error, retry_after 설정 (분석은 판례 없이 계속)
```

- **API로 가져온 판례는 `verified = false`로 시작**하고 화면에 "검수 전"으로 표시합니다. 판례는 AI나 API 응답을 그대로 믿으면 안 되는 데이터라서, 사람이 확인하면 `verified = true`, `verified_by`, `verified_at`을 채웁니다.
- `comparison_limit`("이 판례를 현재 사고에 그대로 적용하면 안 되는 이유")은 협회 도표에서 가져온 판례에는 지금 코드가 직접 쓰고 있습니다. API로 가져온 판례는 비워 둘 수 있으므로, 비어 있을 때 화면에 기본 안내 문구를 보여주는 규칙이 필요합니다.
- API 오류는 분석 전체를 실패시키지 않고 "판례 없이" 진행하는 것을 추천합니다.

## 7. 세션과 영상 보관

로그인이 없는 MVP라서 **소유 토큰(`accident.session_id`)**이 유일한 접근 제어입니다.

1. 사고를 만들 때 서버가 `session_id`(무작위 UUID)를 발급하고 브라우저(쿠키 또는 로컬 저장소)에 보관합니다.
2. 이후 요청은 이 값을 함께 보내고, 서버는 해당 사고의 `session_id`와 일치할 때만 응답합니다.
3. `accident.expires_at`이 지나면 정리 작업이 원본 영상 파일을 삭제하고 `video.deleted_at`을 기록합니다. 행은 남겨서 처리 이력을 추적합니다.
4. **영상 저장·추가 활용에 동의한 사용자만** 영상을 계속 보관하고, 보관하는 것은 **비식별본뿐**입니다(`retention_consent_at`). 원본은 세션이 끝나면 삭제합니다. 동의하지 않으면 비식별본도 삭제하고 분석 결과(JSON)만 남깁니다. 이 경우 타임라인 화면은 영상 없이 보이거나, 사용자가 자기 영상 파일을 다시 선택해 재생합니다(지금 프론트에 이미 있는 기능).
5. **원본과 비식별본의 만료를 다르게** 둘 수 있습니다. 원본은 비식별이 잘못됐을 때 다시 처리하려고 보관하는 것이므로 더 짧게 두는 걸 추천합니다.

> ⚠️ 현재 [main.py](../../backend/main.py)는 `uploads/` 전체를 `/files`로 누구나 접근하게 열어 둡니다. 원본 영상이 URL만 알면 보이는 상태이므로, 서명 URL과 `session_id` 확인으로 바꿔야 합니다. (코드 수정이라 별도로 진행합니다)

## 8. 마이그레이션

- 지금은 저장소가 서버 메모리이고 DB에 데이터가 없으므로 **옮길 데이터가 없습니다.** 새 스키마로 바로 만들면 됩니다.
- 앞으로 스키마가 계속 바뀔 예정이라 `schema.sql` 한 파일 방식 대신 **Alembic** 같은 마이그레이션 도구를 쓰는 걸 추천합니다. `requirements.txt`에 SQLAlchemy가 이미 있습니다.
- `updated_at`은 DB가 자동으로 갱신하지 않으므로 서비스 코드가 상태를 바꿀 때 함께 갱신합니다. (원하면 트리거로 바꿀 수 있습니다)

## 합의가 필요한 항목

1. **`timeline` 테이블을 없애고 `result` JSONB에 넣어도 되는지.** 타임라인을 조건으로 검색할 일이 있으면 테이블로 유지해야 합니다.
2. **원본 영상 보관 기간.** `accident.expires_at`과 `video.expires_at`에 얼마를 줄지(예: 원본 24시간, 비식별본 7일)와, 세션의 정의(브라우저를 닫으면 끝인지, 시간으로 정하는지).
3. **수집 동의 기록 수준.** 버전과 시각만 저장해도 되는지, 동의한 IP나 기기 정보까지 필요한지(개인정보라 최소화를 추천).
4. **API로 가져온 판례를 검수 전에 화면에 보여줄지.** 보여준다면 "검수 전" 표시 문구, 안 보여준다면 검수 전까지는 참고에서 제외.
5. **지원하지 않는 사고 유형의 기록.** `unsupported` 사고도 영상과 함께 보관할지, 즉시 삭제할지.
6. **과실표 버전 관리.** 과실표가 바뀌면 이전 분석 결과와 어떻게 구분할지. `analysis.csv_sha256`으로 구분하는 것을 제안합니다.
7. ~~저장하는 영상은 무엇인가.~~ **결정됨: 영상 저장·추가 활용에 동의해도 비식별본만 저장합니다.** 원본은 세션이 끝나면 동의 여부와 상관없이 삭제합니다.
8. **프레임 이미지는 저장하지 않습니다.** 분석 결과는 프레임 번호와 초 단위 시각만 담고, 화면의 장면 이미지는 보관한 영상에서 그 시각을 뽑아 보여줍니다. 영상을 보관하지 않으면 이미지는 보여줄 수 없습니다.
