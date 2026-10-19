# 팀 검토 안내 (SJI 브랜치 머지 전)

`SJI` 브랜치에서 백엔드를 새로 만들고, 프론트와 분석 모델을 연결했습니다. 머지하기 전에 무엇이 바뀌었고 누가 무엇을 봐야 하는지 정리했습니다. 작성 기준일은 2026-10-19입니다.

## 1. 한 줄 요약
영상 업로드 → 동의 → 번호판·사람 비식별화 → AI 분석 → 사고 상황 확인 → 가감요소 질문 → 결과·타임라인·판례까지 **서버와 연결된 전체 흐름**이 만들어졌습니다. 서비스는 **차대차 사고(133개 유형)만** 지원하고, 그 밖의 사고는 `unsupported`로 끝납니다.

## 2. 무엇이 바뀌었나

| 영역 | 변경 | 자세한 문서 |
|---|---|---|
| 백엔드 | 초안을 버리고 FastAPI + PostgreSQL로 새로 작성. API 서버와 worker(작업 처리기)로 분리 | [backend/README.md](../backend/README.md) |
| API | 세션(`X-Session-Id`) 기반, 사고당 영상 1개(약 15초, 최대 20초), 분석 상태·단계, 확인·확정, 서명된 영상 URL | [api.md](api.md) |
| DB | `migrations/`의 순수 SQL 마이그레이션. 작업 큐(`job`) 포함 | [db/schema-v0.4-proposal.md](db/schema-v0.4-proposal.md) |
| 분석 모델 | `Avly.py`(5천 줄)를 `backend/model/avly/` 패키지로 분할. 데이터·프롬프트는 파일로 분리. **원본 `Avly.py`와 노트북은 마지막 정리까지 남겨 둠** | [backend/model/avly/README.md](../backend/model/avly/README.md) |
| 비식별화 | `backend/plate/redact.py`: 번호판은 검은 박스, 사람은 전체 블러. 실패하면 영상을 만들지 않고 멈춤(fail-closed). 비식별된 영상만 저장·분석에 사용 | prd-reference §10 |
| 판례 | DB 먼저, 없으면 API로 보충. 공통점·차이점은 규칙 기반(퍼센트 없음) | api.md |
| 프론트 | 가짜 데이터 제거, 서버 연결. 사전 설문·퀴즈 동의·영상 증거·텔레메트리 제거 | [frontend/README.md](../frontend/README.md), [frontend-structure.md](frontend-structure.md) |
| 개인정보 | 분석 동의(필수), 영상 저장·활용 동의(선택). 원본은 세션 종료(24시간)에 삭제. 차대차가 아닌 영상은 동의와 무관하게 24시간 뒤 삭제 | [review/consent-review.md](review/consent-review.md) |

문서 정리: v0.3·v0.4 초안 API 문서와 v0.3·v0.4 초안 SQL(`schema.sql`, `schema-v0.4-draft.sql`)은 구현으로 대체되어 삭제했습니다. 필요하면 git 기록에서 볼 수 있습니다.

## 3. 검증한 것과 못 한 것

| 검증함 | 검증 못 함 |
|---|---|
| 백엔드 테스트 109개(실제 PostgreSQL 17), 프론트 테스트 30개, eslint, 빌드 | **실제 OpenAI(GPT) 분석** (키 없이 가짜 엔진으로만 시험) |
| 실제 docker compose 스택에 HTTP 요청, 브라우저(Playwright) 전체 흐름 39개 항목 | 실제 법령·판례 API (`law_api`) |
| YOLO 비식별화 속도와 동작(별도 환경) | worker 이미지 안에서의 실제 YOLO, 실제 영상 재생 품질 |

## 4. 검토 요청

| 담당 | 볼 것 | 파일 |
|---|---|---|
| 법무·개인정보 | 동의 문구, 외부 AI 전송(국외 이전) 고지, 보관 기간 | [review/consent-review.md](review/consent-review.md) |
| 문구 검수 | 가감요소 20개와 법령 풀이의 쉬운 말 (전부 검수 전, 법령 풀이 7개는 비어 있음) | [review/easy-words-review.md](review/easy-words-review.md) |
| 모델 담당 | Gemini 전환 시 바뀌는 범위, 평가 영상 준비 | [review/gemini-switch.md](review/gemini-switch.md) |
| 백엔드 | API·DB 구조, worker 방식(한 번에 한 작업), 마이그레이션 | api.md, backend/README.md |
| 프론트 | 새 화면 흐름, 서버 오류 처리, 문구 | frontend-structure.md |
| 기획 | 가감요소 확장(133개 중 7개 등록), PDF 필요 여부, 사고 유형 오판 시 되돌리기 | prd-reference.md §9 |

## 5. 머지 전에 알아둘 것
- `SJI`에는 `main` 대비 커밋이 120개 쌓여 있고 변경 파일은 229개입니다. 모델 원본(`Avly.py`, 노트북, `results/`)이 포함돼 있어 크게 보입니다.
- `backend/.env`가 있어야 compose가 시작됩니다. `.env.example`을 복사하세요. 팀 공용 DB(`DATABASE_URL`)에는 마이그레이션이 자동으로 돌지 않습니다(`AUTO_MIGRATE` 기본 꺼짐).
- 기본 개발 모드는 **가짜 분석 + 비식별 없는 복사**입니다. 실제 분석은 `ENGINE=avly REDACTION=yolo INSTALL_YOLO=true`와 `OPENAI_API_KEY`가 필요합니다.
- 실행 방법은 루트 [README.md](../README.md)를 보세요.

## 6. 남은 일
1. 실제 영상으로 분석 품질 확인(프롬프트 조정 포함), 평가용 영상과 정답 라벨 준비
2. 법무 검토 후 동의 문구 확정
3. 쉬운 말 검수 반영, 법령 풀이 7개 작성
4. 가감요소 규칙 확장 (7/133)
5. Gemini 전환 여부 결정 (유료 키, 평가 영상 필요)
6. 저장 동의 영상의 삭제 시점 정책
7. 서버 PDF 여부, 원본 `Avly.py`·노트북·`results/` 정리
