export const REPORT_SUMMARY = {
  code: "AV-24901",
  accidentType: "차선 변경 중 접촉 사고",
};

export const REASONS = [
  {
    title: "표준 과실 기준 (30:70)",
    badge: "기본율 적용",
    highlight: false,
    text: "동일 방향 진행 중 진로 변경 사고의 표준 과실 기본도표(제252호)에 따라 피변경 차량 30%, 진로변경 차량 70%를 기준값으로 시작합니다.",
  },
  {
    title: "상대측 신호 미표시 (-5%p)",
    badge: "-5%p 감산",
    highlight: true,
    text: "진로변경 30m 전 방향지시등을 점등하지 않은 상대 차량의 명백한 도로교통법 제38조 위반이 영상 분초 단위(24.3초)로 확인되었습니다.",
  },
  {
    title: "근접 급진입 및 불가항력 (-5%p)",
    badge: "-5%p 추가 감산",
    highlight: true,
    text: "안전거리 미확보 상태에서 차간 4.2m로 진입하였으며, 인지반응시간(0.8초) 내 충돌 회피가 물리적으로 불가능했음이 텔레메트리로 검증되었습니다.",
  },
];

export const TELEMETRY = [
  { icon: "speed", label: "충돌 1.5초 전 내 속도", value: "46 km/h", note: "제한속도 50km/h 내", tone: "safe" },
  { icon: "timer", label: "충돌여유시간 (TTC)", value: "0.72 초", note: "회피 한계 도달", tone: "danger" },
  { icon: "airline_stops", label: "제동 반응 시간", value: "0.31 초", note: "즉각 브레이크 작동", tone: "safe" },
];

export const EVIDENCES = [
  {
    title: "상대 차량 방향지시등 미점등",
    badge: { text: "99.8% 미동작", className: "red-badge" },
    text: "진입 전 3개 연속 프레임(초당 30fps) 픽셀 조도 추적 결과 방향지시등 비활성 상태가 정밀 입증되었습니다.",
    images: [
      { src: "https://lh3.googleusercontent.com/aida-public/AB6AXuDyFN-05PM9yPQEbJUu5ievvfxLz8gy_hViKmNIOd0GjsDSWf83KCHmQhOXyik1VEtzPtbN_f6omzwfEcHw99RDRMQR2AT_S13ZTT7qCT_e6fGx2rCl7O6ncuQt2LteSxtLJSoj591KrbiLLscQRXx4j4_h-jvtAV6GgMhhOM2Yo7Q2AjabucLzbLp5-Drq7ryw0pyPvbhV-xRkmsUbp89e6O63G2RYmmCd3IDdTxLecHxJDc4jMvKtbQ", time: "00:23.8" },
      { src: "https://lh3.googleusercontent.com/aida-public/AB6AXuAtjtEhlS-EpPWbP6dvXoSBo9A8RHK_wCUkidqq3svDWGyAzu-h6KFQf42BOo9uKoVsW453na31QcwtaAdIkZ2bt909JONKGa6OAhkpyYDdDR1Bs2rvadZHzRmK5YwFf5Z4WHE0nDM5c6WOFcgHQks8orudneWXY2_qDDjfQnlYEyTs3n6d0_5zTeXtLekyM0PlSGOzCMvSr_TnSmMHs4F9G0C3Zm--CKem5EQg2N-UF5fJbGU0dXsi4A", time: "00:24.1" },
      { src: "https://lh3.googleusercontent.com/aida-public/AB6AXuB52Ur2821Rqxas0JWQ9pqOJHYzz1hUl7y2CO38vN2nfS377n-fZKCGcjHSrrJDvq5zn1ReBGzjfibhdlOMn2y-eXOREKmlNENH0k3qwoF27CriqHVAWxwVCMTXX3fQXntmNcDQOF8y-xzm5OtaoUSpueq269KoTgYMyZOIRWk-4C6_Zs23UzLWHUwvl9S60N3_asAAXTH1QNnziOHkSoKmF6LNPtTsOxTeKanpqcxzotySW8MW4UPC0A", time: "00:24.5" },
    ],
  },
  {
    title: "규정속도 준수 및 직진 차선 유지",
    badge: { text: "46km/h 준수", className: "green-badge" },
    text: "GPS 센서 데이터 및 도로 차선 간격 분석 결과, 내 차량은 제한속도(50km/h) 이하로 2차로 중심선 정중앙을 유지하고 있었습니다.",
    detail: { icon: "gps_fixed", text: "차로 이탈률 0.04m 이내 (안정적 직진 주행 완료)" },
  },
  {
    title: "무리한 급진입 및 제동 불가항력",
    badge: { text: "TTC 0.72초", className: "red-outline-badge" },
    text: "인간 운전자의 평균 제동 인지 반응 시간 (0.7초~1.0초)을 밑도는 시점에 급격히 유입되어 충돌 회피 기회가 물리적으로 결여되었습니다.",
    detail: {
      icon: "gavel",
      text: "대법원 2018다293282 '회피 불능 신뢰의 원칙' 부합",
      className: "danger-text",
    },
  },
];
