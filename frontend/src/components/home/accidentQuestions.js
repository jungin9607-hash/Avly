export const QUESTION_STEPS = [
  {
    title: "첫 번째 분석을 위한 추가 질문",
    description: "사고 당시 내 차량과 운전자의 상태를 선택해 주세요. 알 수 없는 항목은 ‘모름’을 선택해 주세요.",
    submitLabel: "다음 질문으로",
    questions: [
      { key: "vehicleCondition", text: "사고 당시 내 차의 컨디션은 어땠나요?", options: ["이상 없음", "타이어·브레이크 이상", "기타", "모름"] },
      { key: "driverCondition", text: "사고 당시 운전자의 상태는 어땠나요?", options: ["정상", "졸음·피로", "주의 분산", "기타", "모름"] },
      { key: "speed", text: "사고 직전 내 차량의 운전 속도는 어느 정도였나요?", options: ["정차", "30km/h 이하", "31~50km/h", "51~80km/h", "81km/h 이상", "모름"] },
    ],
  },
  {
    title: "두 번째 분석을 위한 추가 질문",
    description: "사고 당시의 도로 환경, 날씨와 내 차량 진행 방향의 신호를 선택해 주세요.",
    submitLabel: "답변 제출하고 분석 시작하기",
    questions: [
      { key: "roadType", text: "사고가 발생한 도로 형태는 무엇인가요?", options: ["일반 직선 도로", "교차로", "곡선 도로", "고속도로·자동차 전용도로", "기타", "모름"] },
      { key: "roadSurface", text: "사고 당시 노면 상태는 어땠나요?", options: ["건조", "젖음", "눈·결빙", "기타", "모름"] },
      { key: "visibility", text: "주변 장애물로 시야가 가려졌나요?", options: ["시야 양호", "차량에 가려짐", "시설물·수목 등에 가려짐", "기타", "모름"] },
      { key: "weather", text: "사고 당시 날씨는 어땠나요?", options: ["맑음", "비", "눈", "안개", "기타", "모름"] },
      { key: "signal", text: "사고 직전 내 차량 진행 방향의 신호는 무엇이었나요?", options: ["신호 없음", "녹색", "황색", "적색", "모름"] },
    ],
  },
];
