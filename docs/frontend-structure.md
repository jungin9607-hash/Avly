# 프론트엔드 구조 가이드

`frontend/src` 기준입니다. 화면은 소개, 업로드(분석 흐름), 결과, 타임라인, 판례 다섯 개입니다.

## 폴더 구조

```
src/
├─ App.jsx, routes.js            라우팅과 경로 정의 (경로 문자열은 routes.js에서만 만든다)
├─ api/                          서버 연결
│  ├─ config.js, session.js      서버 주소, 세션(session_id) 보관
│  ├─ client.js                  fetch 래퍼 (X-Session-Id, 오류 → 한국어 문구)
│  ├─ adapters.js                서버 응답 → 화면용 모양 변환 (+ adapters.test.js)
│  ├─ useAnalysis.js             분석 상태를 주기적으로 조회하는 훅
│  └─ fixtures/                  테스트용 예시 응답
├─ pages/                        화면별 폴더. 각 폴더 안에 components/(그 화면의 조각), hooks/(그 화면의 훅)
│  ├─ common/                    여러 화면이 같이 쓰는 것: TopNav, AnalysisGate(분석 id로 결과를 불러와 상태별로 보여줌),
│  │                             CaseBasisNotice, LegalNotice(지금은 쓰는 곳 없음), useNavigationBackdrop
│  ├─ intro/                     /
│  ├─ home/                      /upload  (Home.jsx + components/ 모달·업로드 영역 + hooks/useAnalysisFlow.js 흐름 상태)
│  ├─ report/                    /analysis/:id
│  ├─ time/                      /analysis/:id/timeline
│  └─ law/                       /analysis/:id/law
├─ assets/, styles/
```

## 분석 흐름 (`/upload`)

`useAnalysisFlow`(reducer 훅)가 단계를 관리하고 `Home.jsx`가 `FlowModals`로 단계에 맞는 모달을 보여 줍니다.

```
동의 → 업로드 → 진행(서버 조회) ─┬→ 사고 상황 확인(장소 → 유형 → 내 차 → 상대 차) → 가감요소 질문 → 결과 화면으로 이동
                                 ├→ 지원하지 않는 사고 안내
                                 └→ 오류 안내
```

- 사고 상황 확인의 선택지는 서버의 `/catalog/accident-types`에서 받고, 앞 항목을 고르면 뒤 항목의 보기를 좁힙니다 (`cascade`, `resolveOption`, `normalizeSelection`).
- 결과 화면은 `AnalysisGate`가 상태(진행 중, 확인 대기, 지원 안 함, 실패, 완료)에 맞는 화면을 고릅니다.
- 결과 상태 `final / partial / base_only / unresolved`에 따라 보여 주는 내용이 다릅니다 (`pages/report/reportContent.js`).

## 무엇을 고치려면 어디를 보나

| 하고 싶은 일 | 파일 |
| --- | --- |
| 서버 응답 모양이 바뀜 | `api/adapters.js` (+ 테스트) |
| 분석 흐름 단계 추가·변경 | `pages/home/hooks/useAnalysisFlow.js`, `pages/home/components/FlowModals.jsx` |
| 동의 문구 | `pages/home/components/ConsentModal.jsx` (법률 검토 전 문구) |
| 결과 화면 문구·상태별 안내 | `pages/report/reportContent.js`, `pages/report/components/StatusNotice.jsx` |
| 타임라인 / 판례 화면 문구 | `pages/time/`, `pages/law/lawContent.js` |
| 법적 안내 | `pages/common/components/CaseBasisNotice.jsx`, `pages/time/components/TimelineNotice.jsx` |
| 경로 변경 | `routes.js` |

## 원칙

- **서버가 주지 않은 값은 만들어 보여 주지 않는다.** 속도, G값, 충돌 시각 확정, 판례 유사도 퍼센트 등은 없다.
- 서버의 쉬운 말 문장은 그대로 보여 준다.
- CSS는 전역으로 번들링되므로 클래스명이 겹치지 않게 화면별 접두사를 쓴다 (`uh-` 업로드, `md-` 업로드 모달, `si-` 소개, `ar-` 결과, `tl-` 타임라인, `law-` 판례, `ag-` 분석 게이트, `tn-` 상단 메뉴). CSS 파일은 그 컴포넌트·화면 옆에 두고, 색은 `styles/colors.css`, 글꼴은 `styles/fonts.css`에서만 정한다.
- 화면 안에서만 쓰는 조각은 그 화면의 `components/`에, 두 화면 이상이 쓰면 `pages/common/`에 둔다.
