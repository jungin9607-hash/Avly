import { Link } from "react-router-dom";
import { ROUTES } from "../../../routes";
import "./LawPageLink.css";

export default function LawPageLink({ analysisId }) {
  return (
    <div className="tl-law-link-area">
      <Link to={ROUTES.law(analysisId)} className="tl-law-link">
        <strong>유사 판례 바로가기</strong>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M5 12h14M13 6l6 6-6 6" />
        </svg>
      </Link>
    </div>
  );
}
