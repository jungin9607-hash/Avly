import { BrowserRouter, Routes, Route } from "react-router-dom";
import Intro from "./page/intro/intro";
import Home from "./page/home/home";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* 처음 접속하면 인트로 화면 */}
        <Route path="/" element={<Intro />} />

        {/* 홈 화면 */}
        <Route path="/home" element={<Home />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;