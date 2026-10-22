# 🚗 Avly

AI 기반 블랙박스 사고 분석 서비스

> **현재 지원 범위**: 차대차 사고(과실표 133개 유형)의 기본 과실비율은 모두 안내합니다. **가감산 비율은 사람이 검수를 끝낸 사고 유형과 가감요소만** 지원하고, 나머지는 기본 비율만 안내하거나 "확인한 요소만 반영한 비율"로 안내합니다.
> 지원하는 유형은 [docs/review/supported-types.md](docs/review/supported-types.md), 검수가 남은 항목은 [docs/review/pending-review-requests.md](docs/review/pending-review-requests.md)에 있습니다.

---

# 개발 환경

필수 설치 프로그램

- Git
- VS Code
- WSL2 (Ubuntu)
- Docker Desktop

---

# 최초 1회 설정

## 1. Ubuntu(WSL) 실행

Windows에서

```
Ubuntu
```

검색 후 실행

또는

```powershell
wsl
```

---

## 2. 프로젝트 Clone

Ubuntu 터미널에서

```bash
cd ~

git clone https://github.com/xxxxx/Avly.git

cd Avly
```

---

## 3. VS Code 열기

```bash
code .
```

왼쪽 아래에

```
WSL: Ubuntu
```

가 표시되면 정상입니다.

---

## 4. Docker Desktop 설정

Docker Desktop 실행

```
Settings
→ Resources
→ WSL Integration

☑ Enable integration
☑ Ubuntu

Apply & Restart
```

(최초 1회만)

---

## 5. develop 브랜치 이동

```bash
git checkout develop
```

---

## 6. 프로젝트 실행

```bash
docker compose up --build
```

(최초 1회, 코드나 requirements가 바뀌었을 때도)

이후에는

```bash
docker compose up
```

db(로컬 PostgreSQL), backend, worker, frontend가 함께 뜹니다. **어느 DB를 쓰는지는 `backend/.env`의 `DATABASE_URL` 한 줄로 정합니다.**
팀 공용 DB(Supabase)를 쓰면 팀원이 같은 판례 저장분과 분석 결과를 같이 보고, 로컬 DB(`postgresql://postgres:avly@db:5432/avly`)를 쓰면 내 PC에만 쌓입니다. 자세한 내용은 [backend/README.md](backend/README.md#데이터베이스-공용-db와-로컬-db)를 보세요.
분석 모드는 **`backend/.env`의 `ENGINE`, `REDACTION`**을 그대로 따릅니다. 예제 설정은 실제 분석(`avly`, `yolo`)이며 API 키와 YOLO 포함 worker 이미지가 필요합니다.
키 없이 화면 흐름만 시험하려면 명시적으로 `ENGINE=fake`, `REDACTION=dev_copy`를 지정하세요. 이 모드의 결과는 실제 영상 분석이 아닙니다.

---

# 접속 주소

Frontend

```
http://localhost:5173
```

Backend

```
http://localhost:8000/docs
```

(`backend/.env` 파일이 있어야 compose가 시작됩니다. `backend/.env.example`을 복사해 만드세요. 개발 모드에서는 키를 채우지 않아도 됩니다.)

---

# 종료

```bash
docker compose down
```

---

# 협업

브랜치 생성 및 Git 규칙은

👉 CONTRIBUTING.md 참고
---

# 문서

- 백엔드 실행·구조·환경변수·테스트: [backend/README.md](backend/README.md)
- 프론트 구조: [frontend/README.md](frontend/README.md), [docs/frontend-structure.md](docs/frontend-structure.md)
- API 명세 (프론트 연동): [docs/api.md](docs/api.md)
- 서비스 범위와 결정 사항 (PRD 참고): [docs/prd-reference.md](docs/prd-reference.md)
- 날짜별 변경 정리: [docs/changes-2026-10-20.md](docs/changes-2026-10-20.md)
