import { describeAnalysis } from "../../../api/adapters";
import useAnalysis from "../../../api/useAnalysis";
import NoticeScreen from "./NoticeScreen";
import "./AnalysisGate.css";

// 결과 화면 세 개(분석 결과·타임라인·유사 판례)가 함께 쓰는 문지기.
// 분석이 끝나서 결과가 있을 때만 children({ analysis, session }) 을 그리고, 아니면 사정에 맞는 안내를 보여 준다.
export default function AnalysisGate({ analysisId, active, children }) {
  const { session, expired, analysis, error, loading, retry } = useAnalysis(analysisId);

  if (analysis?.status === "completed") {
    const engine = analysis.engine ?? analysis.result?.analysis_engine;
    return (
      <>
        {["fake", "replay"].includes(engine) && (
          <p className="ag-test-notice" role="status">시험용 결과입니다. 업로드한 영상을 AI로 분석한 내용이 아닙니다. 실제 분석 모드에서 새로 분석해 주세요.</p>
        )}
        {children({ analysis, session })}
      </>
    );
  }

  const notice = describeAnalysis({ session, analysis, error, loading, analysisId, expired });
  return <NoticeScreen active={active} notice={notice} onRetry={retry} />;
}
