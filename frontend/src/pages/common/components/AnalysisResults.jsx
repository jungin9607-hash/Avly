import { NavLink, Outlet, useParams } from "react-router-dom";
import AnalysisGate from "./AnalysisGate";
import TopNav from "./TopNav";
import { ROUTES } from "../../../routes";
import "./AnalysisResults.css";

// 분석 결과를 한 번 불러오고 세 탭이 같은 분석과 세션을 공유한다.
export default function AnalysisResults() {
  const { analysisId } = useParams();
  const tabs = [
    { label: "분석결과", to: ROUTES.report(analysisId), end: true },
    { label: "타임라인", to: ROUTES.timeline(analysisId) },
    { label: "유사판례", to: ROUTES.law(analysisId) },
  ];

  return (
    <AnalysisGate analysisId={analysisId} active="분석 결과">
      {(context) => (
        <div className="analysis-results">
          <TopNav theme="clear" showNewAnalysis />
          <header className="analysis-results-heading">
            <nav className="analysis-results-tabs" aria-label="사고 분석 결과 상세">
              {tabs.map(({ label, to, end }) => (
                <NavLink key={to} to={to} end={end}>
                  {label}
                </NavLink>
              ))}
            </nav>
          </header>
          <div className="analysis-results-content">
            <Outlet context={context} />
          </div>
        </div>
      )}
    </AnalysisGate>
  );
}
