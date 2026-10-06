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

(최초 1회)

이후에는

```bash
docker compose up
```

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

- 백엔드 실행·구조: [backend/README.md](backend/README.md)
- API 명세 (프론트 연동): [docs/api.md](docs/api.md)
