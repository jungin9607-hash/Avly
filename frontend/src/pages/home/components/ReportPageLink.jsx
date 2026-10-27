import { Link } from "react-router-dom";
import useAnalysis from "../../../api/useAnalysis";
import { lastAnalysisId } from "../../../api/session";
import { ROUTES } from "../../../routes";
import "./ReportPageLink.css";

// 이 브라우저에서 만든 가장 최근 분석이 끝났을 때만 나타나는 "분석 결과 바로가기". 누르면 그 결과 화면으로 간다.
export default function ReportPageLink() {
  const id = lastAnalysisId();
  const { analysis } = useAnalysis(id);
  if (!id || analysis?.status !== "completed") return null;
  return (
    <Link to={ROUTES.report(id)} className="uh-report-link">
      <strong>분석 결과 바로가기</strong>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="m9 6 6 6-6 6" />
      </svg>
    </Link>
  );
}
