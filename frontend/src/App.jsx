import { BrowserRouter, Routes, Route } from "react-router-dom";
import Intro from "./page/intro/intro";
import Home from "./page/home/home";
import Report from "./page/report/report";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* 처음 접속하면 인트로 화면 */}
        <Route path="/" element={<Intro />} />

        {/* 홈 화면 */}
        <Route path="/home" element={<Home />} />

        {/* 분석 리포트 */}
        <Route path="/report" element={<Report />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;