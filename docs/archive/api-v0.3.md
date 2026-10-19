# Avly API 명세 (v0.3 초안)

> 📝 **초안입니다.** 프론트 화면이 확정되지 않아 필드와 흐름이 바뀔 수 있습니다.
> 바꾸고 싶은 부분은 [맨 아래 합의 항목](#합의가-필요한-항목)에 의견을 남겨 주세요.
>
> 🧪 **현재 분석 결과와 판례는 모두 Mock(가짜) 데이터입니다.** `is_mock: true`로 표시됩니다.
> 서버를 재시작하면 데이터가 모두 사라집니다.

## 공통 규칙

| 항목 | 규칙 |
| --- | --- |
| Base URL | `http://localhost:8000` (개발) |
| API 경로 | `/api/v1/...` (상태 확인만 `/health`) |
| 요청/응답 형식 | JSON (`Content-Type: application/json`). 영상 업로드만 `multipart/form-data` |
| 필드명 | `snake_case` |
| 식별자 | UUID 문자열 (예: `"3b1e219c-a518-4258-a853-50ef4d34b303"`) |
| 시간 | UTC 기준 ISO 8601 (예: `"2026-10-06T04:44:09.863527Z"`). 화면에서는 로컬 시간으로 변환 |
| 인증 | 없음 (MVP) |
| CORS | `http://localhost:5173` 허용 (백엔드 `CORS_ORIGINS`로 변경 가능) |

Swagger에서 직접 호출해 볼 수 있습니다: http://localhost:8000/docs

## 사용자 흐름

```
사고 생성 → 영상 업로드 → (설문 저장) → 분석 시작 → 분석 상태 polling → 결과 표시 → (리포트)
POST        POST           POST          POST         GET (반복)
/accidents  /videos        /survey       /analyses    /analyses/{id}
```

## 목차

| 메서드 | 경로 | 설명 | 성공 코드 |
| --- | --- | --- | --- |
| GET | `/health` | 서버 상태 확인 | 200 |
| POST | `/api/v1/accidents` | 사고 생성 | 201 |
| GET | `/api/v1/accidents/{accident_id}` | 사고 조회 | 200 |
| POST | `/api/v1/accidents/{accident_id}/videos` | 영상 업로드 | 201 |
| POST | `/api/v1/accidents/{accident_id}/survey` | 설문 응답 저장 | 201 |
| POST | `/api/v1/accidents/{accident_id}/analyses` | 분석 시작 | 202 |
| GET | `/api/v1/analyses/{analysis_id}` | 분석 상태·결과 조회 | 200 |
| POST | `/api/v1/analyses/{analysis_id}/reports` | PDF 리포트 생성 (미구현) | 501 |

---

## 오류 응답

모든 오류는 같은 형태입니다. 화면 분기는 `code`로 하고, `message`는 사용자에게 보여줄 수 있는 문구입니다.

```json
{
  "error": {
    "code": "ACCIDENT_NOT_FOUND",
    "message": "사고 정보를 찾을 수 없습니다."
  }
}
```

### 요청 검증 오류 (422)

필수 필드 누락, 타입 오류, 잘못된 UUID 형식 등은 FastAPI가 자동으로 검사하고 아래 형태로 반환합니다.
`details`가 추가로 붙고, `field`는 `위치.필드명`입니다 (`body.title`, `path.accident_id` 등).
`details[].message`는 영어로 된 자동 생성 문구이므로 개발 확인용으로만 사용하세요.

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "요청 형식이 올바르지 않습니다.",
    "details": [
      { "field": "body.title", "message": "Field required", "type": "missing" }
    ]
  }
}
```

### 오류 코드 전체

| 상태 | code | 발생 상황 |
| --- | --- | --- |
| 400 | `EMPTY_FILE` | 0바이트 파일 업로드 |
| 404 | `ACCIDENT_NOT_FOUND` | 존재하지 않는 `accident_id` |
| 404 | `ANALYSIS_NOT_FOUND` | 존재하지 않는 `analysis_id` |
| 404 | `NOT_FOUND` | 존재하지 않는 경로 |
| 405 | `METHOD_NOT_ALLOWED` | 지원하지 않는 HTTP 메서드 |
| 409 | `VIDEO_REQUIRED` | 영상 없이 분석 시작 |
| 409 | `VIDEO_ALREADY_UPLOADED` | 이미 영상이 있는 사고에 다시 업로드 (영상은 사고마다 하나만) |
| 409 | `ANALYSIS_IN_PROGRESS` | 같은 사고의 분석이 이미 진행 중 |
| 409 | `ANALYSIS_NOT_COMPLETED` | 완료되지 않은 분석으로 리포트 요청 |
| 413 | `FILE_TOO_LARGE` | 업로드 용량 초과 (기본 200MB) |
| 415 | `UNSUPPORTED_FILE_TYPE` | 허용하지 않는 확장자 |
| 422 | `VALIDATION_ERROR` | 요청 형식 오류 (위 참고) |
| 500 | `INTERNAL_SERVER_ERROR` | 서버 내부 오류 |
| 501 | `REPORT_NOT_IMPLEMENTED` | PDF 리포트 미구현 |

---

## GET /health

서버가 실행 중인지 확인합니다.

**응답 200**
```json
{ "status": "ok" }
```

---

## POST /api/v1/accidents

사고를 생성합니다. 초기 상태는 `uploaded`입니다.

**요청**
```json
{ "title": "퇴근길 차선 변경 사고" }
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `title` | string | ✅ | 1~200자. 앞뒤 공백은 제거됨 |

**응답 201**
```json
{
  "id": "3b1e219c-a518-4258-a853-50ef4d34b303",
  "title": "퇴근길 차선 변경 사고",
  "status": "uploaded",
  "created_at": "2026-10-06T04:44:09.863527Z"
}
```

**사고 상태 (`status`)**

| 값 | 의미 |
| --- | --- |
| `uploaded` | 생성됨 (분석 전) |
| `analyzing` | 분석 진행 중 |
| `completed` | 최근 분석 완료 |
| `failed` | 최근 분석 실패 |

**오류**: 422

---

## GET /api/v1/accidents/{accident_id}

사고 기본 정보, 현재 상태, 업로드된 영상 목록, 가장 최근 분석 id를 반환합니다.
새로고침 후 화면을 복원할 때 사용할 수 있습니다.

**응답 200**
```json
{
  "id": "3b1e219c-a518-4258-a853-50ef4d34b303",
  "title": "퇴근길 차선 변경 사고",
  "status": "completed",
  "created_at": "2026-10-06T04:44:09.863527Z",
  "videos": [
    {
      "id": "ed577e3b-d331-4805-867f-94f3d5d4224d",
      "accident_id": "3b1e219c-a518-4258-a853-50ef4d34b303",
      "video_url": "http://localhost:8000/files/videos/2d0891f2-8c71-47ed-9056-b23e41e08d52.mp4",
      "thumbnail": null,
      "duration": null,
      "created_at": "2026-10-06T04:44:09.902466Z"
    }
  ],
  "latest_analysis_id": "a0ec10a2-7082-4cb9-88bf-a3541853b324"
}
```

| 필드 | 설명 |
| --- | --- |
| `videos` | 업로드 순서(오래된 것부터) |
| `latest_analysis_id` | 분석을 한 번도 시작하지 않았으면 `null` |

**오류**: 404 `ACCIDENT_NOT_FOUND`, 422 (UUID 형식 오류)

---

## POST /api/v1/accidents/{accident_id}/videos

영상 파일을 업로드합니다. **`multipart/form-data`의 `file` 필드**로 보냅니다.

| 제한 | 값 (기본) |
| --- | --- |
| 허용 확장자 | `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm` (대소문자 무관) |
| 최대 용량 | 200MB |

- 서버가 UUID로 파일명을 새로 만들어 저장합니다. 사용자가 올린 파일명은 사용하지 않습니다.
- 한 사고에 여러 번 업로드할 수 있고, 분석에는 **가장 마지막에 올린 영상**을 사용합니다.

**응답 201**
```json
{
  "id": "ed577e3b-d331-4805-867f-94f3d5d4224d",
  "accident_id": "3b1e219c-a518-4258-a853-50ef4d34b303",
  "video_url": "http://localhost:8000/files/videos/2d0891f2-8c71-47ed-9056-b23e41e08d52.mp4",
  "thumbnail": null,
  "duration": null,
  "created_at": "2026-10-06T04:44:09.902466Z"
}
```

| 필드 | 설명 |
| --- | --- |
| `video_url` | `<video src>`에 바로 쓸 수 있는 개발용 URL. 운영에서는 형식이 바뀔 수 있음 |
| `thumbnail` | 썸네일 URL. **추출 기능 미구현으로 현재 항상 `null`** |
| `duration` | 영상 길이(초). **추출 기능 미구현으로 현재 항상 `null`** |

**영상은 사고마다 하나만** 올릴 수 있습니다. 이미 있으면 409 `VIDEO_ALREADY_UPLOADED`입니다.

**오류**: 400 `EMPTY_FILE`, 404 `ACCIDENT_NOT_FOUND`, 409 `VIDEO_ALREADY_UPLOADED`, 413 `FILE_TOO_LARGE`, 415 `UNSUPPORTED_FILE_TYPE`, 422 (`file` 필드 누락)

---

## POST /api/v1/accidents/{accident_id}/survey

사고 관련 질문과 응답을 저장합니다. 여러 번 호출하면 계속 추가됩니다.
분석을 시작할 때 그때까지 저장된 설문을 함께 사용합니다 (실제 AI 연결 후).

**요청**
```json
{
  "answers": [
    { "question": "사고 당시 신호는 무엇이었나요?", "answer": "초록불이었습니다." },
    { "question": "주행 속도는 어느 정도였나요?", "answer": "약 50km/h" }
  ]
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `answers` | array | ✅ | 1~50개 |
| `answers[].question` | string | ✅ | 1~500자 |
| `answers[].answer` | string | ✅ | 1~2000자 |

**응답 201** — 이번 요청에서 저장된 항목만 반환합니다.
```json
{
  "accident_id": "3b1e219c-a518-4258-a853-50ef4d34b303",
  "answers": [
    {
      "id": "9426ec4c-168d-4776-be13-71c311134d0e",
      "accident_id": "3b1e219c-a518-4258-a853-50ef4d34b303",
      "question": "사고 당시 신호는 무엇이었나요?",
      "answer": "초록불이었습니다.",
      "created_at": "2026-10-06T04:44:09.986099Z"
    }
  ]
}
```

**오류**: 404 `ACCIDENT_NOT_FOUND`, 422

---

## POST /api/v1/accidents/{accident_id}/analyses

분석 작업을 시작합니다. 분석은 시간이 걸리므로 **결과를 기다리지 않고 바로 202를 반환**합니다.
이후 `status_url`을 주기적으로 조회(polling)해서 완료 여부를 확인합니다.

요청 본문은 없습니다.

**응답 202**
```json
{
  "analysis_id": "a0ec10a2-7082-4cb9-88bf-a3541853b324",
  "status": "queued",
  "status_url": "/api/v1/analyses/a0ec10a2-7082-4cb9-88bf-a3541853b324"
}
```

`status_url`은 Base URL을 뺀 경로입니다.

**오류**

| 상태 | code | 프론트 처리 예시 |
| --- | --- | --- |
| 404 | `ACCIDENT_NOT_FOUND` | 처음 화면으로 이동 |
| 409 | `VIDEO_REQUIRED` | 영상 업로드 화면으로 안내 |
| 409 | `ANALYSIS_IN_PROGRESS` | `GET /accidents/{id}`의 `latest_analysis_id`로 진행 중인 분석을 이어서 polling |

---

## GET /api/v1/analyses/{analysis_id}

분석 상태와 결과를 조회합니다. **상태와 관계없이 최상위 구조는 항상 같습니다.**

| 필드 | 설명 |
| --- | --- |
| `status` | `queued` → `processing` → `completed` 또는 `failed` |
| `is_mock` | `true`이면 실제 AI가 아닌 개발용 결과. 화면에 "테스트 결과" 표시 권장 |
| `result` | `completed`일 때만 값이 있고, 그 외에는 `null` |
| `error` | `failed`일 때만 값이 있고, 그 외에는 `null` |

### 분석 상태별 응답

**queued / processing** — 대기 중 또는 분석 중. 계속 polling 합니다.
```json
{
  "analysis_id": "a0ec10a2-7082-4cb9-88bf-a3541853b324",
  "accident_id": "3b1e219c-a518-4258-a853-50ef4d34b303",
  "status": "processing",
  "is_mock": true,
  "result": null,
  "error": null
}
```

**completed** — 완료. polling을 멈추고 결과를 표시합니다.
```json
{
  "analysis_id": "a0ec10a2-7082-4cb9-88bf-a3541853b324",
  "accident_id": "3b1e219c-a518-4258-a853-50ef4d34b303",
  "status": "completed",
  "is_mock": true,
  "result": {
    "fault_me": 30,
    "fault_other": 70,
    "confidence": 0.85,
    "summary": "개발용 Mock 분석 결과입니다. 실제 영상을 분석한 결과가 아닙니다.",
    "timeline": [
      {
        "id": "6b5d4a9b-345f-4f02-9477-ffdd3804a2de",
        "time_sec": -3.0,
        "event": "차선 변경 시작",
        "description": "테스트용 사건 설명입니다. 상대 차량이 차선 변경을 시작합니다.",
        "image_url": null
      },
      {
        "id": "89e369b3-6f94-4527-8bec-5b0c5f24b9a5",
        "time_sec": 0.0,
        "event": "충돌",
        "description": "테스트용 사건 설명입니다. 두 차량이 측면으로 충돌합니다.",
        "image_url": null
      }
    ],
    "matched_cases": [
      {
        "case_id": "da2187d2-02eb-42c4-8bb1-fc8f970d1cc0",
        "title": "[테스트용 가상 판례] 차선 변경 중 측면 충돌",
        "summary": "실제 판례가 아닌 개발용 예시입니다. 직진 차량 옆으로 차선을 변경하다 충돌한 상황을 가정한 예시입니다.",
        "fault_ratio": "30:70",
        "similarity": 0.91,
        "source_url": null
      }
    ]
  },
  "error": null
}
```

**failed** — 실패. polling을 멈추고 오류를 표시합니다. 분석 시작 API를 다시 호출하면 재시도할 수 있습니다.
```json
{
  "analysis_id": "891e2931-0b13-40f1-b16e-02d4d20178bc",
  "accident_id": "ca587045-59c9-47e6-82a9-6abcb645a195",
  "status": "failed",
  "is_mock": true,
  "result": null,
  "error": {
    "code": "ANALYSIS_FAILED",
    "message": "사고 분석 중 오류가 발생했습니다. 다시 시도해 주세요."
  }
}
```

### result 필드

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `fault_me` | int | 내 과실 0~100 |
| `fault_other` | int | 상대 과실 0~100. `fault_me + fault_other = 100` 보장 |
| `confidence` | float | 분석 신뢰도 0~1 |
| `summary` | string | 사고 요약 |
| `timeline` | array | **`time_sec` 오름차순** 정렬 |
| `timeline[].time_sec` | float | 충돌 시점이 `0`, 충돌 전은 음수, 충돌 후는 양수 (초) |
| `timeline[].image_url` | string \| null | 해당 시점 장면 이미지. 현재 `null` |
| `matched_cases` | array | 유사 판례, **`similarity` 내림차순** 정렬 |
| `matched_cases[].fault_ratio` | string | `"내 과실:상대 과실"` 형식 (예: `"30:70"`) |
| `matched_cases[].similarity` | float | 유사도 0~1 |
| `matched_cases[].source_url` | string \| null | 판례 원문 링크. Mock 판례는 `null` |

> ⚠️ 현재 `matched_cases`는 **테스트용 가상 판례**입니다. 실제 판례가 아니므로 화면에서 실제 판례처럼 보여주지 마세요.

**오류**: 404 `ANALYSIS_NOT_FOUND`, 422

---

## POST /api/v1/analyses/{analysis_id}/reports

PDF 리포트를 생성합니다. **현재 미구현**이며, 완료된 분석에 요청하면 501을 반환합니다.
존재하지 않는 PDF URL을 반환하지 않습니다.

**응답 501**
```json
{
  "error": {
    "code": "REPORT_NOT_IMPLEMENTED",
    "message": "PDF 리포트 생성 기능은 아직 구현되지 않았습니다."
  }
}
```

**오류**: 404 `ANALYSIS_NOT_FOUND`, 409 `ANALYSIS_NOT_COMPLETED`, 501 `REPORT_NOT_IMPLEMENTED`

구현 후 응답(예정): `201` + `{ "id", "analysis_id", "pdf_url", "created_at" }`

---

## React 사용 예시

### 공통 요청 함수

```js
// src/api/client.js
const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

export async function request(path, { body, ...options } = {}) {
  const isFormData = body instanceof FormData
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    // FormData는 브라우저가 boundary를 포함한 Content-Type을 자동으로 설정하므로 직접 지정하지 않는다.
    headers: isFormData ? options.headers : { 'Content-Type': 'application/json', ...options.headers },
    body: isFormData || body === undefined ? body : JSON.stringify(body),
  })

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const error = data?.error ?? {}
    throw new ApiError(res.status, error.code ?? 'UNKNOWN_ERROR', error.message ?? '요청에 실패했습니다.', error.details)
  }
  return data
}
```

### 사고 생성

```js
import { request } from './client'

export function createAccident(title) {
  return request('/api/v1/accidents', { method: 'POST', body: { title } })
}

// 사용
const accident = await createAccident('퇴근길 차선 변경 사고')
console.log(accident.id)
```

### 영상 업로드 (FormData)

```js
export function uploadVideo(accidentId, file) {
  const formData = new FormData()
  formData.append('file', file) // 필드 이름은 반드시 'file'
  return request(`/api/v1/accidents/${accidentId}/videos`, { method: 'POST', body: formData })
}

// 사용: <input type="file" accept="video/*" onChange={handleFile} />
async function handleFile(e) {
  const file = e.target.files[0]
  if (!file) return
  try {
    const video = await uploadVideo(accidentId, file)
    setVideoUrl(video.video_url)
  } catch (err) {
    if (err.code === 'FILE_TOO_LARGE' || err.code === 'UNSUPPORTED_FILE_TYPE') {
      alert(err.message)
    } else {
      throw err
    }
  }
}
```

### 분석 시작

```js
export function startAnalysis(accidentId) {
  return request(`/api/v1/accidents/${accidentId}/analyses`, { method: 'POST' })
}

// 사용
try {
  const { analysis_id } = await startAnalysis(accidentId)
  setAnalysisId(analysis_id) // 아래 polling 훅에 전달
} catch (err) {
  if (err.code === 'VIDEO_REQUIRED') navigate('/upload')
  else alert(err.message)
}
```

### 분석 상태 polling (React 훅)

완료(`completed`) 또는 실패(`failed`)면 멈추고, 요청 오류가 나도 멈추며,
컴포넌트가 사라지거나 `analysisId`가 바뀌면 진행 중인 요청과 타이머를 취소합니다.

```js
// src/hooks/useAnalysis.js
import { useEffect, useState } from 'react'
import { request } from '../api/client'

const POLL_INTERVAL_MS = 2000
const FINAL_STATUSES = ['completed', 'failed']

export function useAnalysis(analysisId) {
  const [analysis, setAnalysis] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!analysisId) return

    const controller = new AbortController()
    let timerId

    async function poll() {
      try {
        const data = await request(`/api/v1/analyses/${analysisId}`, { signal: controller.signal })
        setAnalysis(data)
        if (!FINAL_STATUSES.includes(data.status)) {
          timerId = setTimeout(poll, POLL_INTERVAL_MS)
        }
      } catch (err) {
        if (err.name === 'AbortError') return // 컴포넌트 종료로 취소된 경우
        setError(err)
      }
    }

    setAnalysis(null)
    setError(null)
    poll()

    return () => {
      controller.abort()
      clearTimeout(timerId)
    }
  }, [analysisId])

  return { analysis, error }
}
```

```jsx
// 사용 예
function AnalysisPage({ analysisId }) {
  const { analysis, error } = useAnalysis(analysisId)

  if (error) return <p>{error.message}</p>
  if (!analysis || analysis.status === 'queued' || analysis.status === 'processing') {
    return <p>분석 중입니다…</p>
  }
  if (analysis.status === 'failed') return <p>{analysis.error.message}</p>

  const { result } = analysis
  return (
    <section>
      {analysis.is_mock && <p>⚠️ 테스트용 결과입니다.</p>}
      <h2>과실 비율 {result.fault_me} : {result.fault_other}</h2>
      <p>{result.summary}</p>
    </section>
  )
}
```

---

## Mock 구현과 실제 구현 예정

| 기능 | 현재 (Mock) | 실제 구현 예정 | 프론트 영향 |
| --- | --- | --- | --- |
| 데이터 저장 | 서버 메모리. 재시작 시 초기화 | PostgreSQL | 없음 |
| 영상 파일 | 백엔드 로컬 폴더, `/files/...`로 누구나 접근 | 객체 스토리지 + 접근 제어 | `video_url` 형식·만료 시간이 생길 수 있음 |
| 영상 길이·썸네일 | `null` | 영상에서 추출 | 값이 채워짐 |
| 사고 분석 | 약 3초 뒤 항상 같은 결과 | AI 모델 | 분석 시간이 길어짐, `is_mock: false` |
| 유사 판례 | 테스트용 가상 판례 3건 | pgvector 기반 RAG 검색 | `source_url`이 채워짐 |
| 타임라인 이미지 | `null` | 장면 캡처 이미지 | `image_url`이 채워짐 |
| PDF 리포트 | 501 | PDF 생성 | 201 + `pdf_url` |

---

## 합의가 필요한 항목

- [ ] 사고 생성 시 `title`을 사용자가 입력하는지, 프론트가 자동으로 만드는지
- [ ] 사고 생성과 영상 업로드를 한 화면에서 연속 호출할지
- [ ] 설문 질문 목록을 프론트가 가질지, 백엔드에서 내려줄지 (현재는 프론트가 질문 문자열을 보냄)
- [ ] 과실 비율 표기: `fault_me`/`fault_other` 숫자 vs 판례의 `"30:70"` 문자열 형식 통일 여부
- [ ] polling 간격 (예시는 2초)과 최대 대기 시간
- [ ] `is_mock`일 때 화면 표시 방식
- [ ] 오류 `message`를 그대로 보여줄지, `code`별로 프론트 문구를 쓸지
- [ ] `thumbnail`, `duration` 필드명 (`thumbnail_url`, `duration_sec`처럼 단위를 이름에 넣을지)
- [ ] 업로드 용량 제한(200MB)과 허용 확장자
- [ ] 시간 표시: UTC로 받아서 프론트에서 한국 시간으로 변환
