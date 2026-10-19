# avly 패키지

`backend/model/Avly.py`(5천 줄짜리 한 파일)를 역할별로 나눈 것입니다.
**동작은 바꾸지 않았습니다.** (아래 "원본과 달라진 점"에 적은 것만 예외)
기존 `Avly.py`는 모든 검증이 끝날 때까지 그대로 둡니다.

- 1단계: 파일을 역할별로 분할
- 2단계: 데이터와 프롬프트를 코드 밖 파일로 분리 ← 현재
- 3단계(예정): 덮어쓰기 구조로 쌓인 `_v291`, `_base` 함수들을 하나로 합치기 (실제 영상으로 결과 비교 필요)

## 모듈 지도

아래로 갈수록 위층입니다. **위층은 아래층을 불러 쓸 수 있고, 반대는 안 됩니다.**

| 모듈 | 역할 |
| --- | --- |
| `dataio.py` | `data/`, `prompts/` 파일 읽기, 환경변수 설정 |
| `constants.py` | 단일 값 상수 (모델 이름, 프레임 수 등) |
| `tables.py` | `data/*.json`을 읽어서 표 데이터를 내놓음 |
| `context.py` | 실행 중 여러 함수가 같이 쓰는 상태(`ctx`) |
| `config.py` | 경로 탐색, 비밀키 읽기 |
| `schemas.py` | 모델 응답 형식(Pydantic) |
| `facts.py` | 장면에서 사실을 뽑는 공통 함수 (여러 모듈이 같이 써서 맨 아래에 둠) |
| `vision.py` | OpenAI 호출, 재시도, 응답 캐시 (모델 공급자를 바꿀 때 교체할 곳) |
| `video.py` | 영상 읽기, 프레임 추출 |
| `observation.py` | 관찰 결과 검증과 보정 |
| `matching.py` | CSV 과실표와 비교해서 후보 연결 |
| `law.py` | 법령/판례 API 조회 |
| `adjustments.py` | 기본 과실비율에 가감요소 적용 |
| `timeline.py` | 타임라인 생성 |
| `report.py` | 사용자용 보고서 |
| `survey.py` | 추가 질문 생성, 답변 반영 |
| `pipeline.py` | 분석 전체 흐름 (`run(settings)`) |
| `cli.py` | 터미널 실행 |

## 데이터와 프롬프트 파일

코드를 고치지 않고 이 파일들만 수정하면 됩니다.

| 위치 | 내용 |
| --- | --- |
| `data/adjustment_rules.json` | 유형별 가감요소 (**434개 유형 중 7개만 입력됨**) |
| `data/verified_cases.json` | 유형별 판례 (5개 유형) |
| `data/law_articles.json` | 유형별 관련 법조문 |
| `data/factor_labels.json` | 가감요소 이름 |
| `data/support_labels.json`, `special_labels.json` | 화면 표시용 라벨 |
| `data/survey_options.json` | 설문 선택지 |
| `data/cause_questions.json` | 사고 원인 질문 |
| `prompts/*.txt` | AI에게 보내는 프롬프트 18개 (`role`, `accuracy_rules`, `overview_scan`, `detail_review_rule_01~11`, `csv_match` 등) |
| `dev/confirmed_contexts.json` | 개발용: 특정 영상 결과를 사용자 확인값으로 덮어쓰는 설정 (**기본은 꺼짐**) |

**프롬프트 파일 수정 시 주의:** 파일 앞뒤의 줄바꿈과 공백도 프롬프트의 일부입니다. 에디터가 끝에 줄바꿈을 자동으로 붙이지 않는지 확인하세요.
**JSON 수정 시 주의:** 유형 번호 키(`126` 등)는 JSON에서 문자열로 적고, 읽을 때 숫자로 바꿉니다.

### 환경변수로 덮어쓰기

설정하지 않으면 기본값을 씁니다. (캐시 키에 모델 이름이 들어가므로 모델을 바꾸면 캐시는 새로 쌓입니다.)

| 환경변수 | 기본값 |
| --- | --- |
| `AVLY_VISION_MODEL` | `gpt-4.1` |
| `AVLY_MATCH_MODEL` | `gpt-4.1-mini` |
| `AVLY_STEP_SECONDS` | `0.333…` (프레임 간격) |
| `AVLY_OVERVIEW_MAX_IMAGES` | `80` |
| `AVLY_REVIEW_IMAGES` | `40` |
| `AVLY_REVIEW_HIGH_IMAGES` | `8` |
| `AVLY_PRE_SECONDS` / `AVLY_POST_SECONDS` | `4.0` / `2.0` |
| `AVLY_DEV_OVERRIDES` | (없음) 개발용 확인값 파일 경로 |

## 실행

`backend/model` 폴더에서 실행합니다. (기존: `backend`에서 `python model/Avly.py --video ...`)

```bash
cd backend/model
python -m avly.cli --video "../uploads/영상.mp4"
```

옵션은 기존과 같습니다: `--pick-video`, `--backend`, `--csv`, `--results`, `--show-logs`, `--no-cache`, `--no-survey`.
`python avly/cli.py`처럼 파일을 직접 실행하면 상대 import 때문에 동작하지 않습니다.

## 원본과 달라진 점 (이것 외에는 글자 그대로 옮겼습니다)

1. **전역 변수 → `ctx` 속성.** 원래 모듈 전역이던 `table`, `fps`, `frame_count`, `result_dir`, `client`, `stages`, `meter`,
   `video_hash`, `csv_hash`, `cache_dir`, `places`, `output_path`, `VIDEO_PATH`, `USE_CACHE`, `SHOW_FRAMES` 등 22개를
   `ctx.table`처럼 읽고 씁니다.
2. **명령줄 인자 → `settings` dict.** 원래 `globals()`에 직접 넣던 값을 `cli.py`가 dict로 만들어 `run()`에 넘깁니다.
3. **`globals().get('이름', 기본값)` 5개를 기본값으로 고정.** 노트북에서 값을 미리 넣어 덮어쓰던 용도였습니다.
4. **`global client` 선언 삭제.** `ctx.client`로 바뀌어서 필요 없어졌습니다.
5. **프롬프트 문자열 18개를 `prompts/*.txt`로 이동.** 코드에서는 `prompt_text('이름')`으로 읽습니다. 내용은 원본과 글자 그대로 같습니다.
6. **표 데이터를 `data/*.json`으로 이동.** 읽어서 예전과 같은 이름의 변수로 내놓습니다.
7. **모델 이름, 프레임 수 등 8개를 환경변수로 덮어쓸 수 있게 함.** 설정하지 않으면 원래 값입니다.
8. **⚠️ 동작이 달라지는 유일한 부분: 특정 영상 강제 덮어쓰기를 껐습니다.**
   원본에는 영상 해시(`8b39e7085d03…`, `32c427bcca53`)를 키로 삼아, 그 영상에서는 모델이 본 값 대신
   "사용자 확인값"(상대 차 진로변경, 회전교차로 등)으로 결과를 덮어쓰는 `CONFIRMED_VIDEO_CONTEXT`,
   `CONFIRMED_ROAD_CONTEXT`가 있었습니다. 이 값들은 `dev/confirmed_contexts.json`으로 옮기고 **기본은 꺼 두었습니다.**
   그래서 `직선도로(고속)1.mp4`, 회전교차로 영상은 이전 저장 결과와 다르게 나올 수 있습니다.
   예전처럼 보려면 `AVLY_DEV_OVERRIDES=avly/dev/confirmed_contexts.json`을 지정하세요.

## 알려진 제약

- **분석을 동시에 두 개 실행할 수 없습니다.** `ctx`가 프로세스에 하나뿐입니다. (원래 전역 변수였을 때와 같은 제약)
  서버(FastAPI)에서 여러 요청을 받으려면 이 부분을 요청별 객체로 바꾸는 작업이 따로 필요합니다.
- **같은 이름 함수의 "덮어쓰기" 구조를 그대로 유지했습니다.** `_v291`, `_base` 같은 함수들은 새 버전이 이전 버전을 불러 쓰는
  연결 구조라서 지울 수 없습니다. 하나로 합치는 건 3단계 작업입니다.
- 코드 안에 `accident_type == 126` 같은 **특정 유형 번호 분기가 약 17곳** 남아 있습니다. 3단계에서 다룹니다.
- 프롬프트 중 100자 미만 짧은 문장과, 사용자에게 보이는 안내 문구(`TIMELINE_NOTICE`, `REPORT_NOTICE` 등)는 아직 코드 안에 있습니다.

## 검증

원본 `Avly.py`와 비교해서 확인했습니다. (원본이 남아 있는 동안 다시 돌려볼 수 있습니다.)

- 함수·클래스 **211개 본문이 원본과 구조(AST)까지 같음** (위 1, 4, 5번의 치환만 예외)
- 실행 흐름(`run`) 22개 문장이 원본과 같음
- 표·상수 **36개가 1단계 사본과 타입·키 순서까지 같음** (`tuple`, 숫자 키 포함)
- 프롬프트 18개 파일 내용이 원본 문자열과 같음
- 환경변수 덮어쓰기와 개발용 설정이 의도대로 동작함
- 18개 모듈이 모두 import 되고, 함수가 호출 시점에 쓰는 전역 이름이 모두 존재함

**실제 영상으로 실행해 보지는 못했습니다.** 개발 PC에 영상과 필요한 패키지(cv2, openai 등)가 없어서,
외부 패키지는 가짜 모듈로 대체해서 import만 확인했습니다.
