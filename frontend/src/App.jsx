import { BrowserRouter, Routes, Route } from "react-router-dom";
import Intro from "./pages/intro/Intro";
import Home from "./pages/home/Home";
import Report from "./pages/report/Report";
import Time from "./pages/time/Time";
import Law from "./pages/law/Law";

// 화면 라우팅은 App에서 관리하고 각 화면은 pages 폴더에 둔다.
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/upload-test" element={<Home />} />
        <Route path="/analysis-test" element={<Report />} />
        <Route path="/timeline-test" element={<Time />} />
        <Route path="/law" element={<Law />} />
        <Route path="*" element={<Intro />} />
      </Routes>
    </BrowserRouter>
  );
}