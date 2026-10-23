// 화면 주소. 분석 결과 화면들은 분석 번호(analysisId)를 주소에 담아서, 새로고침해도 같은 결과를 다시 불러온다.
export const ROUTES = {
  home: "/upload",
  report: (id) => `/analysis/${id}`,
  timeline: (id) => `/analysis/${id}/timeline`,
  law: (id) => `/analysis/${id}/law`,
  document: (id) => `/analysis/${id}/report`, // 인쇄·PDF 저장용 보고서
  resume: (id) => `/upload?resume=${id}`,
};
