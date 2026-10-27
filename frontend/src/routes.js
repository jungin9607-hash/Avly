// 화면 주소. 분석 결과 화면들은 분석 번호(analysisId)를 주소에 담아서, 새로고침해도 같은 결과를 다시 불러온다.
export const ROUTES = {
  home: "/upload",
  report: (id) => `/analysis/${id}`,
  timeline: (id) => `/analysis/${id}/timeline`,
  law: (id) => `/analysis/${id}#similar-cases`, // 유사 판례는 분석 결과 화면 안(저장·공유 아래)에 있다
  document: (id) => `/analysis/${id}/report`, // 인쇄·PDF 저장용 보고서
  resume: (id) => `/upload?resume=${id}`,
};

// 분석 번호 없이 들어가는 주소. 최근 분석이 있으면 그 결과로, 없으면 "블랙박스 영상을 먼저 올려 주세요" 안내를 보여 준다.
export const LATEST_ROUTES = {
  report: "/analysis",
  timeline: "/timeline",
  law: "/law",
};
