export const NAV_ITEMS = [
  { key: "home", label: "홈", to: "/home", icon: "home" },
  { key: "report", label: "분석 결과", to: "/report", icon: "analytics" },
  {
    key: "analysis",
    label: "사고 분석",
    icon: "error_outline",
    children: [
      { label: "사고 순간 타임라인", to: "/time" },
      { label: "유사 판례 분석", to: "/law" },
    ],
  },
  { key: "prevention", label: "사고 예방", to: "/home", icon: "verified_user" },
];

// 현재 경로에서 활성화할 메뉴 key (인트로 화면은 홈으로 표시)
export const getActiveKey = (pathname) => {
  if (pathname === "/" || pathname === "/home") return "home";
  if (pathname === "/report") return "report";
  if (pathname === "/time" || pathname === "/law") return "analysis";
  return null;
};
