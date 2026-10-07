# AVLY Frontend

React 19 and Vite frontend for the AVLY traffic-accident analysis service.

## Screens

| Route | Screen | Main content |
| --- | --- | --- |
| `/` | Intro | Service introduction and entry point to analysis |
| `/home` | Home | Video upload, analysis questionnaire, progress, result summary, and reanalysis flow |
| `/report` | Report | Fault-ratio summary, supporting evidence, and report sharing/download actions |

## Navigation

- The intro, home, and report screens use the same navigation order: 홈, 분석 결과, 사고 분석, 사고 예방.
- Desktop navigation uses a hover/focus submenu for 사고 분석.
- On narrow screens, navigation switches to a right-side full-height drawer with a dimmed backdrop. 사고 분석 can be opened with its separate expand control.
- Navigation uses React Router and keeps transitions inside the app. The current report page marks 분석 결과 as active.
- The home result-confirmation button, “사고 상황이 일치합니다,” closes the analysis modal and navigates to `/report`.
- 사고 순간 타임라인 and 사고 예방 do not have separate routes yet; they currently link to `/home`. 유사 판례 분석 links to `/report`.
- The report’s “산정 근거 확인” button and its associated modal were removed.

## Development

```bash
npm run dev
npm run build
```

The frontend can also be run with the repository's Docker Compose setup. The production build was verified with `docker compose exec frontend sh -lc "npm run build"`.
