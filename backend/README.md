# Avly Backend (v0.3)

FastAPI 백엔드입니다. 지금은 **AI·PostgreSQL 없이** 로컬에서 실행되는 Mock 버전입니다.

> ⚠️ **데이터는 메모리에만 저장됩니다.** 서버를 재시작하면(코드 수정으로 `--reload`가 동작할 때 포함)
> 사고, 설문, 분석 결과가 모두 초기화됩니다. 업로드한 영상 파일은 `backend/uploads/`에 남지만
> 서버는 더 이상 그 파일을 기억하지 못합니다.

API 명세(프론트 연동용): [docs/api.md](../docs/api.md)

---

## 실행 방법 1: Windows PowerShell (Python 직접 실행)

Python 3.12 이상이 필요합니다.

```powershell
cd backend

# 1) 가상환경 생성 (최초 1회)
python -m venv .venv

# 2) 가상환경 활성화
#    "스크립트를 실행할 수 없습니다" 오류가 나면 아래 줄을 먼저 실행하세요.
#    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

# 3) 패키지 설치 (최초 1회, requirements.txt 가 바뀌었을 때)
pip install -r requirements.txt

# 4) 환경변수 파일 만들기 (최초 1회)
Copy-Item .env.example .env

# 5) 서버 실행
uvicorn main:app --reload
```

## 실행 방법 2: Docker (WSL, 팀 공통 환경)

프로젝트 루트에서 실행합니다. `requirements.txt`가 바뀌었으므로 **처음 한 번은 `--build`가 필요합니다.**

```bash
docker compose up --build
```

## 접속 주소

| 용도 | 주소 |
| --- | --- |
| Swagger 문서 (API 직접 테스트) | http://localhost:8000/docs |
| ReDoc 문서 | http://localhost:8000/redoc |
| 상태 확인 | http://localhost:8000/health |

---

## 처음 테스트하는 순서 (Swagger)

http://localhost:8000/docs 에서 각 API의 **Try it out → Execute**를 누릅니다.

1. `GET /health` → `{"status": "ok"}`
2. `POST /api/v1/accidents` → `{"title": "테스트 사고"}` 입력 → 응답의 `id` 복사
3. `POST /api/v1/accidents/{accident_id}/videos` → `id` 붙여넣기, mp4 파일 선택
4. `POST /api/v1/accidents/{accident_id}/survey` → 설문 응답 저장 (선택)
5. `POST /api/v1/accidents/{accident_id}/analyses` → 응답의 `analysis_id` 복사
6. `GET /api/v1/analyses/{analysis_id}` → 처음엔 `queued`/`processing`, 약 3초 뒤 `completed`

---

## 환경변수 (`.env`)

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 요청을 허용할 프론트 주소 (쉼표 구분) |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | `video_url` 생성에 쓰는 백엔드 주소 |
| `UPLOAD_DIR` | `uploads` | 업로드 저장 폴더 (상대 경로는 `backend/` 기준) |
| `MAX_UPLOAD_SIZE_MB` | `200` | 영상 최대 용량 |
| `ALLOWED_VIDEO_EXTENSIONS` | `.mp4,.mov,.avi,.mkv,.webm` | 허용 확장자 |
| `MOCK_ANALYSIS_DELAY_SECONDS` | `3` | Mock 분석 완료까지 걸리는 시간 |

---

## 폴더 구조

```
backend/
  main.py              앱 조립: CORS, 라우터, 오류 처리, /files 정적 파일
  app/
    config.py          환경변수 설정
    models.py          내부 데이터 구조 (9개 테이블 초안)
    schemas.py         API 요청·응답 형식 (Pydantic)
    errors.py          통일된 오류 응답
    routers/           URL ↔ 서비스 연결
    services.py        업무 로직
    repository.py      메모리 저장소        ← PostgreSQL 로 교체할 부분
    storage.py         로컬 파일 저장소      ← S3 등 객체 스토리지로 교체할 부분
    analyzer.py        Mock AI / Mock 판례 검색 ← 실제 AI, pgvector RAG 로 교체할 부분
```

요청 흐름: `routers` → `services` → `repository` / `storage` / `analyzer`

## Mock 으로 동작하는 부분

| 기능 | 현재 | 교체 예정 |
| --- | --- | --- |
| 데이터 저장 | 메모리 (`repository.py`) | PostgreSQL |
| 영상 저장 | `backend/uploads/videos/`, `/files`로 누구나 접근 가능 | 객체 스토리지 + 접근 제어 (서명 URL 등) |
| 영상 길이·썸네일 | 추출하지 않음 → `null` | ffmpeg 등으로 추출 |
| 사고 분석 | 고정 결과 반환 (`analyzer.analyze_accident`) | AI 모델 |
| 유사 판례 | 테스트용 가상 판례 3건 (`analyzer.search_similar_cases`) | pgvector RAG |
| 분석 작업 실행 | 서버 프로세스 내 백그라운드 작업 | 필요 시 작업 큐 (Celery/RQ 등) |
| PDF 리포트 | 501 반환 | PDF 생성 |
