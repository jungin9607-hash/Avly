# Avly Backend (v0.4)

FastAPI API 서버와 **worker**(분석 작업 실행기)로 이루어져 있습니다. 데이터는 PostgreSQL에 저장됩니다.

- API 명세: [docs/api.md](../docs/api.md)
- 서비스 범위와 결정 사항: [docs/prd-reference.md](../docs/prd-reference.md)
- 분석 모델(`avly` 패키지): [model/avly/README.md](model/avly/README.md)

## 구성

```
브라우저 ─▶ backend (FastAPI)  ─▶ PostgreSQL ◀─ worker ─▶ avly 모델 / OpenAI / 판례·법령 API
              요청 접수, 조회        상태·결과·job      영상 처리, 분석, 결과 계산
```

API 서버는 분석을 직접 하지 않고 DB의 `job` 표에 일을 넣습니다. worker가 그 표를 보고 한 번에 하나씩 처리합니다.
(avly 모델이 전역 상태를 쓰기 때문에 worker는 한 번에 한 작업만 합니다.)

## 실행

프로젝트 루트에서 (db, backend, worker, frontend가 함께 뜹니다):

```bash
docker compose up --build
```

기본 설정은 **키 없이 전체 흐름을 시험하는 개발 모드**입니다 (`ENGINE=fake`, `REDACTION=dev_copy`, 로컬 db 사용, 마이그레이션 자동 적용).
이 모드에서는 실제 AI 분석도, 실제 비식별화도 하지 않습니다.

| 용도 | 주소 |
| --- | --- |
| Swagger | http://localhost:8000/docs |
| 상태 확인 | http://localhost:8000/health, /health/db |
| 프론트 | http://localhost:5173 |

## 환경변수 (`backend/.env`, 예시는 `.env.example`)

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `DATABASE_URL` | (필수) | PostgreSQL 주소. compose는 로컬 db로 덮어쓴다 (`DEV_DATABASE_URL`로 바꿀 수 있음) |
| `AUTO_MIGRATE` | `false` | 시작할 때 `migrations/*.sql` 적용. **공용 DB 보호를 위해 기본은 끔.** compose의 로컬 db에서만 켠다 |
| `APP_SECRET` | 개발용 값 | 영상 서명 URL 비밀값. 운영에서는 반드시 바꾼다 |
| `SESSION_TTL_HOURS` | `24` | 이 시간이 지나면 원본 영상을 삭제한다 |
| `UNSUPPORTED_RETENTION_HOURS` | `24` | 차대차가 아니라 분석하지 않은 영상(원본·비식별본)을 저장 동의와 상관없이 이 시간 뒤 삭제한다 |
| `ENGINE` | `avly` | `fake`(키 없이 시험) / `replay`(저장 결과 재생) / `avly`(실제 분석) |
| `REDACTION` | `yolo` | `yolo`(번호판·사람 탐지, 운영) / `dev_copy`(가리지 않고 복사만, **운영 금지**) |
| `OPENAI_API_KEY` | | `ENGINE=avly`에 필요 |
| `law_api` | | 판례·법령 API 키. 없으면 판례 보충을 건너뛴다 |
| `CORS_ORIGINS`, `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB`, `ALLOWED_VIDEO_EXTENSIONS` | | 기존과 같다 |

**실제 분석으로 돌리려면:** `backend/.env`에 `OPENAI_API_KEY`, `law_api`를 넣고 `ENGINE=avly`, `REDACTION=yolo`로 바꾼 뒤
worker 이미지를 YOLO 포함으로 빌드한다: `INSTALL_YOLO=true docker compose up --build worker`.
(이 조합은 아직 실제 영상으로 끝까지 검증하지 못했다.)

개발 중 `ENGINE=fake`에서는 영상 파일 첫 줄의 지시로 상황을 만들 수 있다. 목록은 [docs/api.md](../docs/api.md#개발테스트).

## 테스트

DB 테스트는 **실제 PostgreSQL**이 필요하고, 테스트마다 `public` 스키마를 비우므로 **빈 DB**를 쓰세요. 공용 DB를 가리키면 안 됩니다.

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt -r requirements-model.txt
TEST_DATABASE_URL=postgresql://postgres:x@localhost:5432/postgres \
PYTHONPATH=.:model python -m unittest discover -s tests -t . -v     # API, worker, 판례, 마이그레이션 등
PYTHONPATH=.:model python -m unittest model.avly.test_explain       # 쉬운 말 설명
python -m unittest plate.test_redact                                 # 비식별화 (가짜 탐지기)
```

`TEST_DATABASE_URL`이 없으면 DB 테스트는 건너뜁니다. 실제 compose 스택을 HTTP로 확인하는 스크립트: `python tests/e2e_smoke.py`.

## 폴더 구조

```
backend/
  main.py             앱 조립: CORS, 라우터, 오류 처리
  app/
    config.py         환경변수 설정
    db.py             연결, 마이그레이션 실행 (모르는 DB에는 적용하지 않는 안전장치 포함)
    repository.py     DB 읽기·쓰기 (SQL)
    catalog.py        과실표 선택지, 가감요소 질문
    security.py       세션(X-Session-Id), 서명 영상 URL
    storage.py        영상 파일 저장·삭제
    schemas.py, presenters.py, status.py, errors.py, deps.py
    routers/          accidents, analyses, catalog, media
    worker/           runner(작업 반복), engines(fake/replay/avly), finalize(결과 계산),
                      cases·compare(판례 조회와 규칙 기반 비교), redaction, cleanup
  migrations/         0001_initial.sql, 0002_job.sql (적용 기록: schema_migration 표)
  plate/              번호판·사람 비식별화 (redact.py)
  model/avly/         분석 모델 패키지
  tests/              API, worker, 판례, 마이그레이션 테스트와 e2e_smoke.py
```

DB 설계 배경은 [docs/db/schema-v0.4-proposal.md](../docs/db/schema-v0.4-proposal.md)입니다. 설계 초안이 `migrations/0001`이 되었고,
작업 큐(`job` 표, `0002`)와 `finalize` 단계가 추가되었습니다.

## 아직 안 된 것

- 서버 PDF (`POST .../reports`는 501. PDF는 브라우저 인쇄)
- 실제 OpenAI 분석, 판례·법령 API, worker 이미지의 실제 YOLO 모델은 키·영상이 없어 **end-to-end로 검증하지 못함**
- 가감요소 등록은 133개 유형 중 7개
