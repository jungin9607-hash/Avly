import { Link } from "react-router-dom";
import { lastAnalysisId } from "../../../api/session";
import { ROUTES } from "../../../routes";
import "./TopNav.css";

/* 상단 메뉴: 왼쪽 로고 · 오른쪽 메뉴
 * theme="light": 흰 배경 화면용 (흰 바탕 + 검정 글자)
 * theme="dark":  내용이 메뉴 아래로 스크롤되는 어두운 화면용 (반투명 밤색 바탕)
 * 분석 결과·타임라인·유사 판례는 가장 최근에 이 브라우저에서 만든 분석으로 연결되고, 없으면 홈으로 보낸다. */
export default function TopNav({ active, theme }) {
  const id = lastAnalysisId();
  const menu = [
    { label: "홈", to: ROUTES.home },
    { label: "분석 결과", to: id ? ROUTES.report(id) : ROUTES.home },
    { label: "타임라인", to: id ? ROUTES.timeline(id) : ROUTES.home },
    { label: "유사 판례", to: id ? ROUTES.law(id) : ROUTES.home },
  ];
  return (
    <header className={theme ? `tn tn-${theme}` : "tn"}>
      <Link to="/" className="tn-logo">
        Avly <small>에블리</small>
      </Link>
      <nav className="tn-menu">
        {menu.map((m) => (
          <Link key={m.label} to={m.to} className={m.label === active ? "active" : ""}>
            {m.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
