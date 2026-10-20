// 분석 결과 화면의 고정 문구. 사고 내용과 비율, 근거는 서버 결과(api/adapters.js 의 toReportModel)에서 온다.

// 리포트 저장·공유 + 사고 타임라인으로 이동
export const REPORT_ACTIONS = {
  title: "분석 결과 활용하기",
  pdf: "분석 결과 저장",
  share: "공유하기",
  erase: "결과 지우기",
  eraseConfirm: "분석 결과와 올린 영상을 지금 삭제할까요? 삭제하면 되돌릴 수 없어요.",
  timeline: {
    label: "사고 타임라인 바로가기",
  },
};

// 맨 위 큰 비율 위에 붙는 설명 (확정 여부에 따라 다르다)
export const RATIO_LABEL = {
  final: "AI 예상 과실 비율",
  partial: "확인된 요소만 반영한 예상 비율",
  base_only: "기본 과실 비율",
};

// 가감요소 영역 제목 (확정이 아닐 때)
export const FACTOR_TITLE = {
  partial: "이 비율은 어떻게 나왔나요?",
  base_only: "이 비율은 어떻게 나왔나요?",
};
