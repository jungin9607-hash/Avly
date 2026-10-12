export const STAGE = {
  CONSENT: "consent",
  ERROR_FORMAT: "errorFormat",
  ANALYZING: "analyzing",
  REANALYZING: "reanalyzing",
  QUESTIONNAIRE: "questionnaire",
  UNSUPPORTED: "unsupported",
  RESULT: "resultSummary",
  REANALYSIS: "reanalysis",
};

export const ALLOWED_EXTENSIONS = ["mp4", "mov", "avi"];
export const MAX_FILE_SIZE = 500 * 1024 * 1024;

export const MODAL_INFO = {
  [STAGE.CONSENT]: { title: "블랙박스 영상 AI 분석 동의", step: 1 },
  [STAGE.ERROR_FORMAT]: {
    title: "지원하지 않는 형식 또는 용량 초과",
    subtitle: "업로드 파일 사양 확인",
    step: null,
  },
  [STAGE.ANALYZING]: {
    title: "에블리 AI가 영상을 정밀 분석하고 있습니다",
    subtitle: "컴퓨터 비전 텔레메트리 추출 중",
    step: 2,
  },
  [STAGE.REANALYZING]: {
    title: "질문 내용을 반영해 재분석 중입니다",
    subtitle: "답변을 반영하여 사고 상황을 다시 분석하고 있습니다",
    step: 2,
  },
  [STAGE.QUESTIONNAIRE]: { title: "정확한 과실 분석을 위한 AI 추가 질문", step: 3 },
  [STAGE.UNSUPPORTED]: {
    title: "지원하지 않는 사고 유형",
    subtitle: "AI 판독 예외 케이스 감지",
    step: null,
  },
  [STAGE.RESULT]: { title: "AI가 판독한 사고 상황 제시", step: 4 },
  [STAGE.REANALYSIS]: {
    title: "사고 정황 재분석 요청",
    subtitle: "가중치 재조정 파라미터 선택",
    step: null,
  },
};

export const INITIAL_ANSWERS = {
  blinker: "no",
  speed: "limit_ok",
  weather: "clear",
};

export const QUESTIONS = [
  {
    key: "blinker",
    text: "충돌 직전 상대 차량이 방향지시등을 점등했나요?",
    options: [
      { value: "no", label: "켜지 않았다" },
      { value: "yes", label: "켜져 있었다" },
      { value: "unknown", label: "인지하지 못함" },
    ],
  },
  {
    key: "speed",
    text: "내 차량은 제한속도를 준수 중이었나요?",
    options: [
      { value: "limit_ok", label: "규정속도 준수" },
      { value: "limit_over", label: "규정속도 초과" },
    ],
  },
  {
    key: "weather",
    text: "사고 당시 시야 장애 요인이 있었나요?",
    options: [
      { value: "clear", label: "맑음 / 시야 확보" },
      { value: "bad", label: "야간 / 우천 / 안개" },
    ],
  },
];

export const REANALYZE_OPTIONS = [
  {
    value: "not_lane_change",
    title: "차선 변경 사고가 아님",
    description: "교차로 직진·좌회전 또는 다른 사고 유형입니다.",
  },
  {
    value: "signal_violation",
    title: "신호위반 또는 중과실 요소 존재",
    description: "신호위반, 중앙선 침범 등의 상황이 있습니다.",
  },
  {
    value: "vehicle_priority",
    title: "통행 우선권 오인식",
    description: "내 차량의 선진입 상황이 잘못 인식되었습니다.",
  },
];

export const GUIDES = [
  {
    title: "전방 블랙박스 영상 권장",
    text: "상대 차량의 진입 각도, 도로 차선(실선·점선), 노면 표시 및 신호등 점등 상태가 뚜렷하게 식별될수록 분석 오차가 감소합니다.",
  },
  {
    title: "사고 전후 15초 내외 구간",
    text: "충돌 시점 기준 최소 10초 전 진입 단계부터 충돌 직후 5초까지 포함하는 것을 권장합니다.",
  },
  {
    title: "음성 녹음 여부 무관",
    text: "에블리 AI는 시각 좌표 및 차량 움직임을 분석하며 내부 대화나 오디오는 분석에 사용하지 않습니다.",
  },
];

export const isAnalyzingStage = (stage) =>
  stage === STAGE.ANALYZING || stage === STAGE.REANALYZING;
