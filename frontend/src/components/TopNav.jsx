import { Link } from "react-router-dom";
import "./TopNav.css";

// 아직 화면이 없는 메뉴는 "#"로 둠
const MENU = [
  { label: "홈", to: "/upload-test" },
  { label: "분석 결과", to: "/analysis-test" },
  { label: "타임라인", to: "/timeline-test" },
  { label: "유사 판례", to: "#" },
];

/* 상단 메뉴: 왼쪽 로고 · 오른쪽 메뉴
 * theme="light": 흰 배경 화면용 (흰 바탕 + 검정 글자)
 * theme="dark":  내용이 메뉴 아래로 스크롤되는 어두운 화면용 (반투명 밤색 바탕) */
export default function TopNav({ active, theme }) {
  return (
    <header className={theme ? `tn tn-${theme}` : "tn"}>
      <Link to="/" className="tn-logo">
        Avly <small>에블리</small>
      </Link>
      <nav className="tn-menu">
        {MENU.map((m) =>
          m.to === "#" ? (
            <a key={m.label} href="#" className={m.label === active ? "active" : ""}>
              {m.label}
            </a>
          ) : (
            <Link key={m.label} to={m.to} className={m.label === active ? "active" : ""}>
              {m.label}
            </Link>
          )
        )}
      </nav>
    </header>
  );
}
