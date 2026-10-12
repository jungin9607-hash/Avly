# 프론트엔드 구조 가이드

`frontend/src` 기준입니다. 화면 5개(`/`, `/home`, `/report`, `/time`, `/law`)가 같은 헤더·푸터와 데이터 파일을 공유하도록 정리했습니다.

## 폴더 구조

```
src/
├─ App.jsx                    라우팅
├─ components/
│  ├─ layout/
│  │  ├─ Header.jsx           상단 헤더 + 데스크톱 메뉴
│  │  ├─ MobileMenu.jsx       모바일 드로어 메뉴
│  │  ├─ Footer.jsx           법적 고지 + 링크 + 저작권
│  │  └─ layout.css           위 3개의 공통 스타일
│  └─ ui/Icon.jsx             Material Symbols 아이콘 <Icon name="close" />
├─ constants/navItems.js      메뉴 항목 정의 + 현재 경로 → 활성 메뉴 판별
├─ data/                      화면에 보여줄 (현재는 시연용) 데이터
│  ├─ timeline.js             /time 타임라인, 필터
│  ├─ precedents.js           /law 판례, 비교 항목
│  └─ report.js               /report 과실 사유, 텔레메트리, 증거
├─ hooks/useToast.js          토스트 메시지 (자동 사라짐)
└─ page/
   ├─ intro/                  /
   ├─ home/                   /home (업로드 → 분석 모달)
   ├─ report/                 /report
   ├─ time/                   /time
   └─ law/                    /law
```

## 무엇을 고치려면 어디를 보나

| 하고 싶은 일 | 파일 |
|---|---|
| 메뉴 추가/이름 변경/링크 변경 | `constants/navItems.js` (데스크톱·모바일 모두 반영) |
| 헤더·푸터 디자인 변경 | `components/layout/*` (5개 화면 모두 반영) |
| 푸터 안내 문구 | 각 페이지의 `<Footer notice="..." />` |
| 타임라인/판례/리포트 내용 수정 | `data/*.js` |
| 질문 문항, 재분석 사유, 가이드 문구 | `page/home/constants.js` |
| 분석 모달 단계별 화면 | `page/home/stages/*` |
| 분석 진행률 동작 | `page/home/useAnalysisProgress.js` |
| 허용 파일 형식/용량 | `page/home/constants.js` (`ALLOWED_EXTENSIONS`, `MAX_FILE_SIZE`) |

## /home 분석 모달 흐름

`page/home/home.jsx`가 모달 열림 여부(`modalOpen`)와 현재 단계(`stage`)를 들고 있고, `AnalysisModal.jsx`가 `stage`에 맞는 단계 컴포넌트를 보여줍니다.

```
consent ─(동의)→ analyzing ─→ questionnaire ─(제출)→ reanalyzing ─→ resultSummary
   │                                                                 │   │
   ├→ errorFormat (파일 오류)                       일치함 → /report ◄┘   └─(불일치)→ reanalysis ─→ reanalyzing
   └→ unsupported (분석 불가 유형)
```

- 단계 이름은 `constants.js`의 `STAGE`에 모여 있습니다. 문자열을 직접 쓰지 말고 `STAGE.XXX`를 쓰세요.
- 단계별 입력값(동의 체크, 질문 답변 등)은 해당 단계 컴포넌트 안에서만 관리합니다.
- 진행률은 `useAnalysisProgress`가 타이머로 시뮬레이션합니다. 실제 API 연결 시 이 훅을 교체하면 됩니다.

## 스타일 규칙

- CSS는 전역으로 번들링됩니다. 클래스명이 겹치면 다른 화면에 영향을 줄 수 있습니다.
- 공통 헤더/푸터 클래스(`site-header`, `mobile-menu-*`, `site-footer-*`, `brand-*`, `nav-*`)는 `layout.css`에만 정의합니다. 페이지 CSS에 다시 만들지 마세요.
- 페이지 고유 스타일은 각 페이지 CSS에 둡니다 (`time-`, `law-`, `report-` 접두사 사용).
- 알려진 중복: `home.css`와 `report.css`에 각각 `.modal-overlay`, `.modal-header` 등이 따로 있습니다. 공통 `Modal` 컴포넌트로 합치는 것이 다음 정리 후보입니다.

## 다음 정리 후보

- `Modal`, `Breadcrumb`, 과실비율 표시(`FaultRatio`)를 공통 컴포넌트로 분리
- 색상·간격 CSS 변수(디자인 토큰) 도입
- 외부 이미지 URL(`data/*.js`)을 `assets/`로 이전
- 백엔드 API 연결 시 `data/*.js`를 API 응답으로 교체
