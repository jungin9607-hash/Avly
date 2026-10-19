import { Link } from "react-router-dom";
import { lastAnalysisId } from "../../api/session";
import { ROUTES } from "../../routes";
import "./ReportPageLink.css";

export default function ReportPageLink() {
  const id = lastAnalysisId();
  return (
    <Link to={id ? ROUTES.report(id) : ROUTES.home} className="uh-report-link">
      <strong>분석 결과 바로가기</strong>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M5 12h14M13 6l6 6-6 6" />
      </svg>
    </Link>
  );
}
