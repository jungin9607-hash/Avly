import { ROUTES } from "../../../routes";
import NoticeScreen from "./NoticeScreen";

// 아직 이 브라우저에서 분석한 영상이 없을 때 상단 메뉴로 들어온 화면에 보여 줄 안내
const PAGES = {
  report: { active: "분석 결과", body: "영상을 분석하면 예상 과실비율과 그 근거를 보여 드려요" },
  timeline: { active: "타임라인", body: "영상을 분석하면 충돌 전후 장면을 시간 순서로 보여 드려요" },
  law: { active: "유사 판례", body: "영상을 분석하면 내 사고와 비슷한 판례를 찾아 드려요" },
};

export default function NoAnalysis({ page }) {
  const { active, body } = PAGES[page];
  const notice = {
    title: "블랙박스 영상을 먼저 올려 주세요",
    body,
    link: { to: ROUTES.home, label: "블랙박스 영상 올리기" },
  };
  return <NoticeScreen active={active} notice={notice} variant="upload" />;
}
