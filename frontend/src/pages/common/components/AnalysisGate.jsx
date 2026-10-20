import { Link } from "react-router-dom";
import { describeAnalysis } from "../../../api/adapters";
import useAnalysis from "../../../api/useAnalysis";
import { ROUTES } from "../../../routes";
import TopNav from "./TopNav";
import "./AnalysisGate.css";

// 결과 화면 세 개(분석 결과·타임라인·유사 판례)가 함께 쓰는 문지기.
// 분석이 끝나서 결과가 있을 때만 children({ analysis, session }) 을 그리고, 아니면 사정에 맞는 안내를 보여 준다.
export default function AnalysisGate({ analysisId, active, theme, children }) {
  const { session, expired, analysis, error, loading, retry } = useAnalysis(analysisId);

  if (analysis?.status === "completed") return children({ analysis, session });

  const notice = describeAnalysis({ session, analysis, error, loading, analysisId, expired });
  return (
    <div className="ag">
      <TopNav active={active} theme={theme} />
      <main className="ag-main" role="status">
        <h1>{notice.title}</h1>
        {notice.body && <p>{notice.body}</p>}
        <div className="ag-actions">
          {notice.retry && (
            <button type="button" className="ag-button" onClick={retry}>
              다시 불러오기
            </button>
          )}
          {notice.link && (
            <Link className="ag-button" to={notice.link.to}>
              {notice.link.label}
            </Link>
          )}
          {notice.link?.to !== ROUTES.home && (
            <Link className="ag-link" to={ROUTES.home}>
              새 영상 분석하기
            </Link>
          )}
        </div>
      </main>
    </div>
  );
}
