import { useEffect, useRef } from "react";
import TopNav from "../../components/common/TopNav";
import HeroSection from "./components/HeroSection";
import FeaturesSection from "./components/FeaturesSection";
import useIntroScroll from "./hooks/useIntroScroll";
import { HERO, FEATURES, CTA } from "./introContent";
import "./Intro.css";

export default function Intro() {
  const root = useRef(null);
  const driveRef = useRef(null); // RoadScene의 계속 달리는 트윈

  useIntroScroll(root, driveRef);

  // 다른 페이지에서 스크롤을 내린 채로 넘어와도 항상 맨 위(도로 화면)부터 시작
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="si" ref={root}>
      <TopNav />
      <HeroSection content={HERO} driveRef={driveRef} />
      <FeaturesSection content={FEATURES} cta={CTA} />
    </div>
  );
}
