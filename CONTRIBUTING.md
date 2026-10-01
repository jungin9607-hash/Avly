# Git 협업 가이드

---

# 브랜치 구조

```
main
 │
develop
 │
 ├── feature/login
 ├── feature/chat
 ├── feature/backend
 └── feature/frontend
```

---

# 작업 시작

## 1. Ubuntu 실행

Windows에서

```
Ubuntu
```

실행

프로젝트 이동

```bash
cd ~/Avly
```

---

## 2. develop 최신화

```bash
git checkout develop

git pull origin develop
```

---

## 3. 본인 브랜치 생성

예시

```bash
git checkout -b feature/login
```

---

## 4. Docker 실행

```bash
docker compose up
```

---

## 5. 개발

코드 작성

---

## 6. Commit

```bash
git add .

git commit -m "feat: 로그인 구현"
```

---

## 7. Push

```bash
git push -u origin feature/login
```

---

## 8. Pull Request

GitHub에서

```
feature/login
        ↓
develop
```

Pull Request 생성

---

# develop 변경사항 가져오기

```bash
git checkout develop

git pull origin develop

git checkout feature/login

git merge develop
```

---

# 작업 종료

```bash
docker compose down
```

---

# 규칙

✅ feature 브랜치에서 작업

❌ develop 직접 Push 금지

❌ main 직접 Push 금지

PR 후 Merge