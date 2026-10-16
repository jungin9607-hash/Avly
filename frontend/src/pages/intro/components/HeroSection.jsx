import { Fragment, useState } from "react";
import RoadScene from "../scene/RoadScene";
import HeroAnalysisLink from "./HeroAnalysisLink";

// 첫 화면: 밤하늘 별 + 왼쪽 아래 제목 + 오른쪽 스크롤 안내 + 밤바다 위 다리를 달리는 도로 장면
export default function HeroSection({ content, driveRef }) {
  return (
    <section className="si-hero">
      <StarField />

      {/* 문구는 왼쪽 아래(화면 아래 어둠 위)에 크게 두고, 가운데 소실점 풍경은 비워 둠 */}
      <div className="si-hero-text">
        <p className="si-label">{content.label}</p>
        <h1>
          <MultiLine lines={content.titleLines} />
        </h1>
      </div>

      {/* 오른쪽 작은 스크롤 안내 (스페이스바 한 번이면 기능 소개까지) */}
      <p className="si-scroll-hint">
        {content.scrollHint}
        <span className="si-scroll-arrow" aria-hidden="true">↓</span>
      </p>

      {/* 밤바다 위 다리를 달리는 도로 장면 */}
      <RoadScene driveRef={driveRef} />

      {/* 화면 아래 가까운 바닥의 어둠: 다가온 차들이 이 속으로 지나감 */}
      <div className="si-road-shade" />

      {/* 지평선의 은은한 빛 (먼 도로까지 물듦) */}
      <div className="si-sky-glow" />

      <div className="si-fade" />
      <HeroAnalysisLink content={content.action} />
    </section>
  );
}

// 밤하늘 별: 작고 옅은 점만, 아주 일부만 천천히 숨 쉬듯 (위치는 한 번만 무작위 생성)
function makeStars(count) {
  const rand = (a, b) => a + Math.random() * (b - a);
  return Array.from({ length: count }, () => ({
    x: rand(0, 100),
    y: rand(0, 100) ** 1.4 / 100 ** 0.4, // 하늘 위쪽에 더 많이
    size: Math.random() < 0.9 ? rand(0.8, 1.4) : rand(1.6, 2),
    opacity: rand(0.2, 0.65),
    twinkle: Math.random() < 0.15,
    delay: rand(0, 6),
    duration: rand(4, 8),
  }));
}

function StarField({ count = 70 }) {
  const [stars] = useState(() => makeStars(count));

  return (
    <div className="si-stars" aria-hidden="true">
      {stars.map((d, i) => (
        <span
          key={i}
          className={d.twinkle ? "si-star si-twinkle" : "si-star"}
          style={{
            left: `${d.x}%`,
            top: `${d.y}%`,
            width: d.size,
            height: d.size,
            opacity: d.opacity,
            animationDelay: `${d.delay}s`,
            animationDuration: `${d.duration}s`,
          }}
        />
      ))}
    </div>
  );
}

// 문자열 배열을 <br />로 이어 붙임
function MultiLine({ lines }) {
  return lines.map((line, i) => (
    <Fragment key={i}>
      {i > 0 && <br />}
      {line}
    </Fragment>
  ));
}
