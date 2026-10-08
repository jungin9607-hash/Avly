# AVLY Frontend

React 19 and Vite frontend for the AVLY traffic-accident analysis service.

## Screens

| Route | Screen | Main content |
| --- | --- | --- |
| `/` | Intro | Service introduction and entry point to analysis |
| `/home` | Home | Video upload, analysis questionnaire, progress, result summary, and reanalysis flow |
| `/report` | Report | Fault-ratio summary, supporting evidence, and report sharing/download actions |
| `/time` | Time | Accident-moment timeline |
| `/law` | Law | Similar precedent analysis |

## Navigation

- All five screens provide shared navigation for Home, Report, Accident Analysis, and Accident Prevention.
- Accident Analysis is a non-navigating menu trigger. Its submenu links to `/time` (timeline) and `/law` (similar precedents).
- Desktop layouts show the navigation links; narrow layouts use a hamburger button and a right-side drawer.
- Navigation uses React Router. Confirming the recognized accident situation on Home closes the modal and navigates to `/report`.

## Implemented UI (2026-10-08)

- Refined the Intro hero, mascot artwork, feature cards, and responsive layout.
- Added and aligned the consent, analysis-progress, follow-up-question, and situation-result stages in the Home analysis modal. A follow-up analysis stage is also shown after answers or a reanalysis request.
- Centered the recognized accident type in the Home result card, kept its label at the left, and removed the confidence badge.
- Added a breadcrumb to the Law page, matching the Time page's `Accident Analysis > Similar Precedent Analysis` layout.
- Fixed invalid JSX in the Home consent modal and preserved the analysis progress flow.

### Analysis flow status

The Home modal currently uses a simulated analysis flow: consent → progress → follow-up questions → reanalysis progress → situation result. It does not yet receive video-analysis results from an AI API, so deciding whether the video is sufficient and conditionally asking follow-up questions remains pending AI integration.

## Development

```bash
npm run dev
npm run build
npm run lint
```

Run these commands from the `frontend` directory. The frontend can also be run with the repository's Docker Compose setup.
