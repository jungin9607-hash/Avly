# 🚗 Avly

AI 기반 블랙박스 사고 분석 서비스

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
팀 공용 DB(Supabase)를 쓰면 팀원이 같은 판례 저장분과 분석 결과를 같이 보고, 로컬 DB(`postgresql://postgres:avly@db:5432/avly`)를 쓰면 내 PC에만 쌓입니다. 자세한 내용은 [backend/README.md](backend/README.md#데이터베이스-공용-db와-로컬-db)를 보세요. 기본은 **키 없이 시험하는 개발 모드**(가짜 분석, 가리지 않는 비식별화)라
실제 AI 분석이 아닙니다. 실제 분석으로 돌리는 방법과 환경변수는 [backend/README.md](backend/README.md)를 보세요.

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
