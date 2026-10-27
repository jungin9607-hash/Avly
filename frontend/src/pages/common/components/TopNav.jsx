import { Link } from "react-router-dom";
import { ROUTES } from "../../../routes";
import "./TopNav.css";

/* 상단 바: 로고
 * theme="light": 흰 배경 화면용 (흰 바탕 + 검정 글자)
 * theme="dark":  내용이 메뉴 아래로 스크롤되는 어두운 화면용 (불투명 남색 바탕)
 * theme="clear": 사진 배경 화면용 (불투명 남색 바탕, 홈 · 결과 안내 화면)
 */
export default function TopNav({ theme, showNewAnalysis = false }) {
  return (
    <header className={theme ? `tn tn-${theme}` : "tn"}>
      <Link to="/" className="tn-logo">
        Avly <small>에블리</small>
      </Link>
      {showNewAnalysis && (
        <Link to={ROUTES.home} className="tn-new-analysis">
          <span aria-hidden="true">+</span> 새 영상 분석
        </Link>
      )}
    </header>
  );
}
