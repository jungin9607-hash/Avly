import { BrowserRouter, Navigate, Route, Routes, useParams, useSearchParams, useOutletContext } from "react-router-dom";
import Intro from "./pages/intro/Intro";
import Home from "./pages/home/Home";
import { ReportView } from "./pages/report/Report";
import { TimeView } from "./pages/time/Time";
import { LawView } from "./pages/law/Law";
import AnalysisResults from "./pages/common/components/AnalysisResults";
import ReportDoc from "./pages/reportdoc/ReportDoc";
import NoAnalysis from "./pages/common/components/NoAnalysis";
import LoadingPreview from "./pages/loading-preview/LoadingPreview";
import LoadingCrash from "./pages/loading-preview/LoadingCrash";
import LoadingCrashColor from "./pages/loading-preview/LoadingCrashColor";
import { lastAnalysisId } from "./api/session";
import { LATEST_ROUTES, ROUTES } from "./routes";

// 분석 번호 없는 주소(상단 메뉴, 예전 임시 주소 -test)로 들어온 사람을 최근 분석 결과로 보낸다. 최근 분석이 없으면 안내를 보여 준다.
function Latest({ page }) {
  const id = lastAnalysisId();
  return id ? <Navigate to={ROUTES[page](id)} replace /> : <NoAnalysis page={page} />;
}

// 화면 라우팅은 App에서 관리하고 각 화면은 pages 폴더에 둔다.
// 분석 결과 화면들은 주소의 분석 번호로 서버에서 결과를 불러온다.
// 업로드 화면은 ?resume=분석번호 가 바뀌면 처음부터 다시 시작한다. (이미 /upload 에 있을 때 "이어서 확인하기"를 눌러도 화면이 같은 컴포넌트라
// 진행 상태가 초기화되지 않아 아무 일도 일어나지 않던 문제를 막는다.)
function HomeRoute() {
  const [params] = useSearchParams();
  return <Home key={params.get("resume") ?? "new"} />;
}
function ReportRoute() {
  const { analysisId } = useParams();
  const { analysis } = useOutletContext();
  return <ReportView analysis={analysis} analysisId={analysisId} similarCases={<LawView result={analysis.result} />} />;
}
function TimeRoute() {
  const { analysis, session } = useOutletContext();
  return <TimeView result={analysis.result} session={session} />;
}
function ReportDocRoute() {
  const { analysisId } = useParams();
  return <ReportDoc analysisId={analysisId} />;
}
function LawRoute() {
  const { analysisId } = useParams();
  return <Navigate to={ROUTES.law(analysisId)} replace />; // 예전 주소: 분석 결과 안의 유사 판례로
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/upload" element={<HomeRoute />} />
        <Route path="/analysis/:analysisId" element={<AnalysisResults />}>
          <Route index element={<ReportRoute />} />
          <Route path="timeline" element={<TimeRoute />} />
          <Route path="law" element={<LawRoute />} />
        </Route>
        <Route path="/analysis/:analysisId/report" element={<ReportDocRoute />} />
        <Route path="/loading-preview" element={<LoadingPreview />} />
        <Route path="/loading-crash" element={<LoadingCrash />} />
        <Route path="/loading-crash-color" element={<LoadingCrashColor />} />
        <Route path="/upload-test" element={<Navigate to={ROUTES.home} replace />} />
        <Route path={LATEST_ROUTES.report} element={<Latest page="report" />} />
        <Route path={LATEST_ROUTES.timeline} element={<Latest page="timeline" />} />
        <Route path={LATEST_ROUTES.law} element={<Latest page="law" />} />
        <Route path="/analysis-test" element={<Latest page="report" />} />
        <Route path="/timeline-test" element={<Latest page="timeline" />} />
        <Route path="*" element={<Intro />} />
      </Routes>
    </BrowserRouter>
  );
}
