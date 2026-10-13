# AVLY 프론트엔드

AVLY 교통사고 분석 서비스의 React 19 + Vite 프론트엔드입니다.

> 폴더 구조와 수정 위치 안내: [docs/frontend-structure.md](../docs/frontend-structure.md)

## 화면

| 경로 | 화면 | 주요 내용 |
| --- | --- | --- |
| `/` | 인트로 | 서비스 소개 및 분석 시작 진입점 |
| `/upload-test` | 영상 업로드 | 시연 파일 업로드 및 분석 동의·질문 흐름 |
| `/analysis-test` | 분석 결과 | 과실비율 분석 결과와 판단 근거 |
| `/timeline-test` | 타임라인 | 사고 순간 타임라인 |
| `/law` | 유사 판례 | 유사 판례 목록과 내 사고 비교 |

## 네비게이션

- 화면 상단의 공통 메뉴에서 업로드, 분석 결과, 타임라인, 유사 판례 화면으로 이동할 수 있습니다.
- React Router를 사용하며, 화면 컴포넌트는 `src/pages/` 아래 화면별 폴더에 있습니다.

## 폴더 구조

- `src/pages/{intro,home,report,time,law}/`: 각 화면과 화면별 스타일
- `src/components/home/`: 업로드 화면에서만 쓰는 동의·질문 모달
- `src/components/common/`: 여러 화면에서 공유하는 상단 메뉴와 법적 안내
- `src/assets/`: 화면에서 사용하는 이미지
- `src/App.jsx`: URL과 화면 연결

## 구현 현황 (2026-10-08)

- 인트로 히어로, 마스코트 이미지, 기능 카드, 반응형 레이아웃을 다듬었습니다.
- 업로드 화면에 동의·질문 팝업과 시연용 분석 흐름을 제공합니다.

### 분석 흐름 현황

업로드 화면의 모달은 현재 시뮬레이션 흐름으로 동작합니다. 실제 영상 AI 분석 API 연동은 포함되어 있지 않습니다.

## 개발

```bash
npm run dev
npm run build
npm run lint
```

위 명령은 `frontend` 디렉터리에서 실행합니다. 저장소의 Docker Compose 설정으로도 실행할 수 있습니다.
