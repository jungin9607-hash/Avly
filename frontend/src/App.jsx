import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom";
import Intro from "./pages/intro/Intro";
import Home from "./pages/home/Home";
import Report from "./pages/report/Report";
import Time from "./pages/time/Time";
import Law from "./pages/law/Law";
import { lastAnalysisId } from "./api/session";
import { ROUTES } from "./routes";

// 예전 임시 주소(-test)로 들어온 사람을 새 주소로 보낸다. 최근 분석이 없으면 홈으로 보낸다.
function Legacy({ page }) {
  const id = lastAnalysisId();
  return <Navigate to={id ? ROUTES[page](id) : ROUTES.home} replace />;
}

// 화면 라우팅은 App에서 관리하고 각 화면은 pages 폴더에 둔다.
// 분석 결과 화면들은 주소의 분석 번호로 서버에서 결과를 불러온다.
function ReportRoute() {
  const { analysisId } = useParams();
  return <Report analysisId={analysisId} />;
}
function TimeRoute() {
  const { analysisId } = useParams();
  return <Time analysisId={analysisId} />;
}
function LawRoute() {
  const { analysisId } = useParams();
  return <Law analysisId={analysisId} />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/upload" element={<Home />} />
        <Route path="/analysis/:analysisId" element={<ReportRoute />} />
        <Route path="/analysis/:analysisId/timeline" element={<TimeRoute />} />
        <Route path="/analysis/:analysisId/law" element={<LawRoute />} />
        <Route path="/upload-test" element={<Navigate to={ROUTES.home} replace />} />
        <Route path="/analysis-test" element={<Legacy page="report" />} />
        <Route path="/timeline-test" element={<Legacy page="timeline" />} />
        <Route path="/law" element={<Legacy page="law" />} />
        <Route path="*" element={<Intro />} />
      </Routes>
    </BrowserRouter>
  );
}
