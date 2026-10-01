# 🤝 Git 협업 가이드

---

# 브랜치 구조

```
main
 │
develop
 │
 ├── feature/login
 ├── feature/chat
 ├── feature/mypage
 ├── feature/frontend
 └── feature/backend
```

- main : 배포 브랜치
- develop : 개발 브랜치
- feature/* : 개인 작업 브랜치

---

# 작업 시작

### develop 최신화

```bash
git checkout develop

git pull origin develop
```

---

# 본인 브랜치 생성

예시

```bash
git checkout -b feature/login
```

또는

```bash
git checkout -b feature/chat
```

브랜치 이름 규칙

```
feature/기능명
```

예시

```
feature/login
feature/chat
feature/calendar
feature/mypage
feature/frontend
feature/backend
```

---

# 개발 시작

Docker 실행

```bash
docker compose up
```

---

# 작업 완료

```bash
git add .

git commit -m "feat: 로그인 구현"
```

---

# Push

```bash
git push -u origin feature/login
```

---

# Pull Request

GitHub에서

```
feature/login
        ↓
develop
```

으로 Pull Request 생성

---

# Pull 받기

develop 최신화

```bash
git checkout develop

git pull origin develop
```

다시 본인 브랜치로 이동

```bash
git checkout feature/login

git merge develop
```

---

# 커밋 메시지 규칙

```
feat: 새로운 기능

fix: 버그 수정

docs: 문서 수정

style: 코드 스타일 수정

refactor: 리팩토링

chore: 설정 변경
```

예시

```
feat: 로그인 API 구현

fix: 회원가입 오류 수정

docs: README 수정
```

---

# 주의사항

❌ main 브랜치에 직접 Push 금지

❌ develop 브랜치에 직접 Push 금지

✅ 반드시 feature 브랜치에서 작업

✅ Pull Request 후 Merge

---

# 작업 종료

```bash
docker compose down
```
