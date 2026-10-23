# AVLY 프론트엔드

React 19 + Vite 프론트엔드입니다. 백엔드 API와 연결되어 실제 분석 결과를 보여줍니다.

> 폴더 구조와 수정 위치: [docs/frontend-structure.md](../docs/frontend-structure.md) · API: [docs/api.md](../docs/api.md)

## 화면

| 경로 | 화면 |
| --- | --- |
| `/` | 소개 |
| `/upload` | 동의 → 영상 업로드 → 분석 진행 → 사고 상황 확인 → 가감요소 질문 |
| `/analysis/:id` | 과실비율 결과 (단계별 계산, 관련 법령) |
| `/analysis/:id/timeline` | 사고 타임라인 |
| `/analysis/:id/law` | 유사 판례와 내 사고 비교 |

예전 `-test` 경로(`/upload-test` 등)는 새 경로로 이동합니다. 분석 화면은 `?resume=<analysis_id>`로 진행 중인 분석을 이어 볼 수 있습니다.

## 서버 연결

- 서버 주소는 `VITE_API_BASE_URL`(기본 `http://localhost:8000`)입니다.
- 사고를 만들 때 받은 `session_id`를 브라우저에 보관하고 이후 요청에 `X-Session-Id`로 보냅니다 (`src/api/session.js`).
- 서버가 안 켜져 있으면 화면이 안내 문구를 보여 줍니다. 가짜 데이터로 대신 채우지 않습니다.
- `src/api/fixtures/`는 **테스트용 예시 응답**입니다. 화면은 이 값을 쓰지 않습니다.

## 개발

```bash
npm run dev      # 개발 서버
npm run build
npm run lint
node --test      # 단위 테스트 (API 변환, 분석 흐름 상태)
```

위 명령은 `frontend` 디렉터리에서 실행합니다. 저장소 루트의 `docker compose up`으로도 실행됩니다.
브라우저 전체 흐름 시험(Playwright)은 [e2e/README.md](e2e/README.md)를 보세요.
