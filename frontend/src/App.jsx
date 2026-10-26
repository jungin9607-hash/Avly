import { BrowserRouter, Navigate, Route, Routes, useParams, useSearchParams } from "react-router-dom";
import Intro from "./pages/intro/Intro";
import Home from "./pages/home/Home";
import Report from "./pages/report/Report";
import Time from "./pages/time/Time";
import Law from "./pages/law/Law";
import ReportDoc from "./pages/reportdoc/ReportDoc";
import LoadingPreview from "./pages/loading-preview/LoadingPreview";
import LoadingCrash from "./pages/loading-preview/LoadingCrash";
import LoadingCrashColor from "./pages/loading-preview/LoadingCrashColor";
import { lastAnalysisId } from "./api/session";
import { ROUTES } from "./routes";

// 예전 임시 주소(-test)로 들어온 사람을 새 주소로 보낸다. 최근 분석이 없으면 홈으로 보낸다.
function Legacy({ page }) {
  const id = lastAnalysisId();
  return <Navigate to={id ? ROUTES[page](id) : ROUTES.home} replace />;
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
  return <Report analysisId={analysisId} />;
}
function TimeRoute() {
  const { analysisId } = useParams();
  return <Time analysisId={analysisId} />;
}
function ReportDocRoute() {
  const { analysisId } = useParams();
  return <ReportDoc analysisId={analysisId} />;
}
function LawRoute() {
  const { analysisId } = useParams();
  return <Law analysisId={analysisId} />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/upload" element={<HomeRoute />} />
        <Route path="/analysis/:analysisId" element={<ReportRoute />} />
        <Route path="/analysis/:analysisId/timeline" element={<TimeRoute />} />
        <Route path="/analysis/:analysisId/law" element={<LawRoute />} />
        <Route path="/analysis/:analysisId/report" element={<ReportDocRoute />} />
        <Route path="/loading-preview" element={<LoadingPreview />} />
        <Route path="/loading-crash" element={<LoadingCrash />} />
        <Route path="/loading-crash-color" element={<LoadingCrashColor />} />
        <Route path="/upload-test" element={<Navigate to={ROUTES.home} replace />} />
        <Route path="/analysis-test" element={<Legacy page="report" />} />
        <Route path="/timeline-test" element={<Legacy page="timeline" />} />
        <Route path="/law" element={<Legacy page="law" />} />
        <Route path="*" element={<Intro />} />
      </Routes>
    </BrowserRouter>
  );
}
