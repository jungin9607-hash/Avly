// 유사 판례 화면의 고정 문구. 판례 내용과 비교는 서버 결과(api/adapters.js 의 toCaseCards)에서 온다.

export const SECTION = {
  title: "나의 사고와 유사한 판례",
  desc: "내 사고 유형에 연결된 판례예요. 판례를 선택하면 내 사고와 비슷한 점과 다른 점을 볼 수 있어요.",
};

export const SUMMARY = {
  title: "선택한 판례와 비슷한 점",
};

export const GUIDE = {
  text: "유사 판례는 사고 상황의 공통점과 차이점을 참고하기 위한 자료입니다. 판례 요약만 비교한 결과이며, 실제 과실비율은 도로 환경, 차량 속도와 사고 경위에 따라 달라질 수 있습니다.",
};

export const EMPTY = {
  title: "아직 찾은 판례가 없어요",
  text: "이 사고 유형에 연결된 판례를 찾지 못했어요. 판례가 없다고 해서 비율이 달라지는 것은 아니에요.",
};

export const STICKY_BAR = {
  button: "내 사고와 비교하기",
  emptyLabel: "비교할 판례를 선택해 주세요", // 판례를 고르기 전 버튼 문구
  // 판례를 고르면 창 오른쪽 아래 구석에 나타나는 보조 버튼
  result: { label: "분석 결과 바로가기" },
};

// 비교 팝업의 PDF 다운로드 버튼 문구 (공통점·차이점 박스 위 오른쪽)
export const COMPARE_REPORT = {
  button: "PDF 다운로드",
};
