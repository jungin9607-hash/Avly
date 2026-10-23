import { ROUTES } from "../../../routes";
import NoticeScreen from "./NoticeScreen";

// 아직 이 브라우저에서 분석한 영상이 없을 때 상단 메뉴로 들어온 화면에 보여 줄 안내
const PAGES = {
  report: { active: "분석 결과", what: "과실 비율 분석 결과를" },
  timeline: { active: "타임라인", what: "사고 순간 타임라인을" },
  law: { active: "유사 판례", what: "비슷한 사고의 판례를" },
};

export default function NoAnalysis({ page }) {
  const { active, what } = PAGES[page];
  const notice = {
    title: "아직 분석한 영상이 없어요",
    body: `블랙박스 영상을 올려 분석하면 ${what} 볼 수 있어요.`,
    link: { to: ROUTES.home, label: "영상 올리러 가기" },
  };
  return <NoticeScreen active={active} notice={notice} />;
}
