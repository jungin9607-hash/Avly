# 🚗 Avly

AI 기반 블랙박스 사고 분석 서비스

---

# 🛠 Tech Stack

- React + Vite
- FastAPI
- Docker
- Docker Compose

---

# 📦 개발 환경

필수 프로그램

- WSL2
- Ubuntu
- Docker Desktop
- VS Code
- Git

Docker Desktop 설정

```
Settings
→ Resources
→ WSL Integration

☑ Enable integration
☑ Ubuntu

Apply & Restart
```

---

# 🚀 프로젝트 실행

### 저장소 Clone

```bash
git clone https://github.com/jungin9607-hash/Avly.git

cd Avly
```

### develop 브랜치 이동

```bash
git checkout develop
```

### Docker 실행

```bash
docker compose up --build
```

(최초 1회만 build)

이후에는

```bash
docker compose up
```

---

# 접속

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

# 📁 프로젝트 구조

```
Avly
│
├── frontend
├── backend
├── docker-compose.yml
└── README.md
```

---

협업 방법은 **CONTRIBUTING.md**를 참고하세요.