import { BrowserRouter, Routes, Route } from "react-router-dom";
import ScrollIntro from "./components/ScrollIntro";
import UploadHome from "./components/UploadHome";
import AnalysisResult from "./components/AnalysisResult";
import Timeline from "./components/Timeline";

// 새 디자인 테스트: 인트로 → 업로드(홈) → 동의·질문 팝업 → 분석 결과 화면
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/upload-test" element={<UploadHome />} />
        <Route path="/analysis-test" element={<AnalysisResult />} />
        <Route path="/timeline-test" element={<Timeline />} />
        <Route path="*" element={<ScrollIntro />} />
      </Routes>
    </BrowserRouter>
  );
}

// import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";cd fron
// import Intro from "./page/intro/intro";
// import Home from "./page/home/home";
// import Report from "./page/report/report";
// import Law from "./page/law/law";
// import Time from "./page/time/time";
// import ScrollIntro from "./components/ScrollIntro";

// function App() {
//   return (
//     <BrowserRouter>
//       <Routes>
//         {/* 처음 접속하면 인트로 화면 */}
//         <Route path="/" element={<Intro />} />

//         {/* 홈 화면 */}
//         <Route path="/home" element={<Home />} />

//         {/* 분석 리포트 */}
//         <Route path="/report" element={<Report />} />

//         {/* 사고 분석 */}
//         <Route path="/time" element={<Time />} />
//         <Route path="/law" element={<Law />} />

//         {/* 스크롤 인트로 테스트용 (기존 홈과 별개) */}
//         <Route path="/scroll-test" element={<ScrollIntro />} />

//         <Route path="*" element={<Navigate to="/" replace />} />
//       </Routes>
//     </BrowserRouter>
//   );
// }

// export default App;