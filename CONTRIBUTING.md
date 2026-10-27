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
 ├── feature/frontend
 └── fix/docker-node-permissions
```

---

# 작업 시작

## 1. Ubuntu / WSL 실행

Windows에서 Ubuntu 또는 WSL을 실행합니다.

```bash
cd ~/Avly
```

> 프로젝트는 Linux/WSL 환경에서 실행하는 것을 권장합니다. Windows에서 바로 Node/NPM 설치와 Docker 권한 문제가 발생할 수 있습니다.

---

## 2. 본인 브랜치 확인

```bash
git branch
```

---

## 3. develop pull


브랜치 확인

```bash
git pull origin develop
```

---

## 4. 환경 준비

### Docker 실행

```bash
docker compose up --build -d
```

### 프론트엔드 의존성 설치

VS Code의 import 해석은 로컬 워크스페이스를 기준으로 보므로, WSL 환경에서 아래를 실행하는 것이 안전합니다.

```bash
cd ~/Avly/frontend
npm install
```

> node_modules는 커밋하지 않습니다.

> Docker 환경에서는 host의 node_modules를 직접 마운트하지 않는 것이 안전합니다.

### 패키지가 추가·변경되었을 때 (중요)

WSL에서 `npm install`을 해도 **Docker 컨테이너 안에는 설치되지 않습니다.**
컨테이너는 `/app/node_modules` 익명 볼륨을 따로 쓰고, 이 볼륨은 `docker compose up --build`로 컨테이너를 다시 만들어도 그대로 남습니다.

`package.json`이 바뀌었다면 (내가 패키지를 추가했거나, `git pull`로 다른 팀원의 변경을 받았을 때) 아래 둘 다 실행합니다.

```bash
# 1) WSL: VS Code import 인식용
cd ~/Avly/frontend
npm install

# 2) 컨테이너: 실제 실행용
cd ~/Avly
docker compose exec frontend npm install
docker compose restart frontend
```

컨테이너가 실행 중이 아니거나 위 방법으로 해결되지 않으면 볼륨을 새로 만들며 다시 빌드합니다.

```bash
docker compose up --build -V
```

> `-V`(`--renew-anon-volumes`)는 기존 `node_modules` 볼륨을 버리고 새로 만듭니다.

백엔드는 `requirements.txt`가 바뀌면 이미지를 다시 빌드합니다.

```bash
docker compose up --build
```

---

## 5. 개발

코드 작성 후 로컬/도커에서 화면을 확인합니다.

```bash
cd ~/Avly
docker compose up --build -d
```

브라우저 접속

```text
http://localhost:5173
```

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

처음 1회만 `-u` 옵션을 사용하고, 이후에는 아래처럼 간단하게 push합니다.

```bash
git push origin 브랜치명
```

---

## 8. Pull Request

GitHub에서 다음 흐름으로 PR을 생성합니다.

```text
feature/login
        ↓
develop
```

PR 생성 후 코드 리뷰를 거친 뒤 merge 합니다.

---

# develop 변경사항 가져오기

```bash
git checkout develop
git pull origin develop
git checkout feature/login
git merge develop
```

필요 시 충돌 해결 후 다시 commit 합니다.

---

# 작업 종료

```bash
docker compose down
```

---

# Docker / WSL 권한 이슈 주의사항

다음 문제가 발생한 적이 있습니다.

- `Cannot resolve import "react-router-dom"`
- `vite: Permission denied`
- `npm install` 시 `EPERM: operation not permitted`

원인:

- Docker에서 host의 `node_modules`를 마운트하면서 WSL/Windows 권한 충돌 발생
- `node_modules`가 root 소유가 되거나 실행 권한이 깨짐

해결 원칙:

- Docker compose에서 host의 `node_modules`를 직접 bind mount하지 않기
- 컨테이너 내부의 `/app/node_modules`를 Docker가 관리하게 유지
- 프론트엔드 에디터 import 문제 해결을 위해 로컬 WSL에서 `npm install` 수행
- 다른 팀원이 같은 문제를 겪지 않도록 `node_modules`는 Git에 올리지 않기

권장 compose 설정:

```yaml
services:
  frontend:
    build:
      context: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
```

> `/app/node_modules`는 Docker 내부 전용 익명 볼륨으로 관리합니다.

### `Failed to resolve import "패키지명"` 오류

`package.json`과 WSL의 `node_modules`에는 패키지가 있는데 브라우저(Vite)에서 이 오류가 나면, **컨테이너 안에만 패키지가 없는 상태**입니다.

```bash
docker compose exec frontend npm install
docker compose restart frontend
```

자세한 내용은 위의 [패키지가 추가·변경되었을 때](#패키지가-추가변경되었을-때-중요)를 참고합니다.

---

# 규칙

✅ feature 브랜치에서 작업

✅ develop 최신 상태 유지

✅ 커밋 전 테스트 / 실행 확인

✅ `node_modules`는 Git에 포함하지 않기

❌ develop 직접 Push 금지

❌ main 직접 Push 금지

PR 후 Merge

---

# 빠른 실행 요약

```bash
cd ~/Avly
git checkout develop
git pull origin develop
git checkout -b feature/내브랜치
docker compose up --build -d
cd ~/Avly/frontend
npm install
git add .
git commit -m "feat: 작업 내용"
git push -u origin feature/내브랜치
```
