# Avly

# Avly

## 개발 환경

- WSL2
- Docker Desktop
- VS Code
- Git

---

## 1. 최초 설정

### 1) WSL 설치

Ubuntu 설치 후 실행

### 2) Docker Desktop 설치

Settings

Resources

WSL Integration

☑ Enable integration

☑ Ubuntu 체크

Apply & Restart

---

## 2. 프로젝트 받기

```bash
git clone https://github.com/xxxxx/Avly.git

cd Avly

git checkout develop
```

---

## 3. 실행

```bash
docker compose up --build
```

실행 후

Frontend

http://localhost:5173

Backend

http://localhost:8000/docs

---

## 4. 종료

```bash
Ctrl + C
```

또는

```bash
docker compose down
```

---

## 5. 다시 실행

```bash
docker compose up
```

---

## 6. 작업 시작

develop 최신화

```bash
git checkout develop

git pull origin develop
```

브랜치 생성

```bash
git checkout -b feature/기능명
```

예)

```bash
git checkout -b feature/login
```

---

## 7. 작업 완료

```bash
git add .

git commit -m "feat: 로그인 구현"

git push origin feature/login
```

GitHub에서 Pull Request 생성

feature/login → develop

---

## 프로젝트 구조

```
Avly
│
├── frontend
├── backend
├── docker-compose.yml
└── README.md
```