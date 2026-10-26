import { Link } from "react-router-dom";
import { LATEST_ROUTES } from "../../../routes";
import "./ReportPageLink.css";

export default function ReportPageLink() {
  return (
    <Link to={LATEST_ROUTES.report} className="uh-report-link">
      <strong>분석 결과 바로가기</strong>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="m9 6 6 6-6 6" />
      </svg>
    </Link>
  );
}
