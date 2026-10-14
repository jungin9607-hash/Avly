import { useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { useNavigate } from "react-router-dom";
import TopNav from "../../components/common/TopNav";
import RoadScene from "./scene/RoadScene";
import "./Intro.css";

gsap.registerPlugin(ScrollTrigger, useGSAP);

// 밤하늘 별: 작고 옅은 점만, 아주 일부만 천천히 숨 쉬듯 (위치는 한 번만 무작위 생성)
function makeStars() {
  const rand = (a, b) => a + Math.random() * (b - a);
  return Array.from({ length: 70 }, () => ({
    x: rand(0, 100),
    y: rand(0, 100) ** 1.4 / 100 ** 0.4, // 하늘 위쪽에 더 많이
    size: Math.random() < 0.9 ? rand(0.8, 1.4) : rand(1.6, 2),
    opacity: rand(0.2, 0.65),
    twinkle: Math.random() < 0.15,
    delay: rand(0, 6),
    duration: rand(4, 8),
  }));
}

export default function Intro() {
  const root = useRef(null);
  const navigate = useNavigate();
  const driveRef = useRef(null); // RoadScene의 계속 달리는 트윈
  const [stars] = useState(makeStars);

  useGSAP(
    () => {
      // 어둠 레이어는 화면 아래 바깥에서 대기
      gsap.set(".si-fade", { yPercent: 100 });

      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (reduce) return;

      const drive = driveRef.current;

      // 스크롤에 따라: 제목이 걷히고 → 가속하며 도로 속으로 들어가고 →
      // 아래에서 어둠이 차올라 기능 소개 배경과 이어짐
      const heroScroll = gsap
        .timeline({
          defaults: { ease: "none" },
          scrollTrigger: {
            trigger: ".si-hero",
            start: "top top",
            end: "+=700",
            scrub: 1.2,
            pin: true,
            anticipatePin: 1, // 고정이 시작·끝나는 순간 화면이 튀지 않게
          },
        })
        .to(".si-hero-text", { opacity: 0, y: -80, ease: "power1.in", duration: 0.45 }, 0)
        .to(".si-scroll-hint", { opacity: 0, duration: 0.2 }, 0)
        .to(".si-sky-glow", { opacity: 0, duration: 0.6 }, 0)
        .to(".si-skyline", { opacity: 0, duration: 0.5 }, 0)
        .to(".si-stars", { y: -60, opacity: 0, duration: 0.7 }, 0)
        .to(".si-road", { scale: 2.4, ease: "sine.in", duration: 1 }, 0)
        // 확대·가속되면 자글자글 깨져 보이는 아스팔트 알갱이와 바다 잔물결은 먼저 흐려 없앰
        .to([".si-asphalt-tex", ".si-sea-waves"], { opacity: 0, ease: "power1.out", duration: 0.35 }, 0)
        .to(drive, { timeScale: 3, ease: "power1.in", duration: 1 }, 0) // 도로 속으로 들어가며 가속
        .to(".si-fade", { yPercent: 0, ease: "power1.inOut", duration: 0.7 }, 0.3);

      // 기능 소개: 제목·카드·아래 띠가 스크롤에 맞춰 차례로 떠오름
      gsap.from([".si-features h2", ".si-card", ".si-cta-bar"], {
        opacity: 0,
        y: 60,
        stagger: 0.12,
        ease: "power2.out",
        scrollTrigger: {
          trigger: ".si-features",
          start: "top bottom",
          end: "top 30%",
          scrub: 1,
        },
      });

      // 스페이스바 두 번이면 기능 소개까지: 도로 화면에서는 한 번 누를 때마다
      // 정해진 지점(처음 → 도로 애니메이션 끝 → 기능 소개 맨 위)으로 부드럽게 이동.
      // Shift+스페이스바는 반대로. 기능 소개 아래에서는 브라우저 기본 스크롤 그대로
      const features = root.current.querySelector(".si-features");
      let pending = null; // 이동 중인 목표 지점 (빠르게 연달아 눌러도 한 단계씩 넘어가게)
      const onKeyDown = (e) => {
        if (e.code !== "Space" || e.ctrlKey || e.metaKey || e.altKey) return;
        // 버튼·입력칸에서는 스페이스바 원래 동작(누르기, 입력) 유지
        if (e.target.closest?.("button, a, input, textarea, select, [contenteditable]")) return;
        const stops = [0, heroScroll.scrollTrigger.end, features.getBoundingClientRect().top + window.scrollY];
        const y = window.scrollY;
        let target;
        if (e.shiftKey) {
          const base = Math.min(y, pending ?? Infinity);
          if (base > stops[2] + 4) return;
          target = [...stops].reverse().find((s) => s < base - 4);
        } else {
          const base = Math.max(y, pending ?? -Infinity);
          target = stops.find((s) => s > base + 4);
        }
        if (target === undefined) return;
        e.preventDefault();
        pending = target;
        window.scrollTo({ top: target, behavior: "smooth" });
      };
      const onScroll = () => {
        if (pending !== null && Math.abs(window.scrollY - pending) < 2) pending = null;
      };
      // 휠·드래그로 직접 스크롤하면 목표 지점 기억을 지움
      const clearPending = () => {
        pending = null;
      };
      window.addEventListener("keydown", onKeyDown);
      window.addEventListener("scroll", onScroll, { passive: true });
      window.addEventListener("wheel", clearPending, { passive: true });
      window.addEventListener("touchstart", clearPending, { passive: true });
      return () => {
        window.removeEventListener("keydown", onKeyDown);
        window.removeEventListener("scroll", onScroll);
        window.removeEventListener("wheel", clearPending);
        window.removeEventListener("touchstart", clearPending);
      };
    },
    { scope: root }
  );

  return (
    <div className="si" ref={root}>
      <TopNav />

      {/* 인트로 */}
      <section className="si-hero">
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

        {/* 문구는 왼쪽 아래(화면 아래 어둠 위)에 크게 두고, 가운데 소실점 풍경은 비워 둠 */}
        <div className="si-hero-text">
          <p className="si-label">AI 블랙박스 과실 분석</p>
          <h1>
            사고의 순간,
            <br />
            판단의 근거까지
          </h1>
          <p className="si-sub">
            블랙박스 영상으로 사고 상황을 분석하고, 그 과실비율이 나온 근거까지 설명합니다.
          </p>
        </div>

        {/* 오른쪽 작은 스크롤 안내 (스페이스바 두 번이면 기능 소개까지) */}
        <p className="si-scroll-hint">
          스크롤 또는 스페이스바
          <span className="si-scroll-arrow" aria-hidden="true">↓</span>
        </p>

        {/* 밤바다 위 다리를 달리는 도로 장면 */}
        <RoadScene driveRef={driveRef} />

        {/* 화면 아래 가까운 바닥의 어둠: 다가온 차들이 이 속으로 지나감 */}
        <div className="si-road-shade" />

        {/* 지평선의 호박색 빛 (먼 도로까지 은은하게 물듦) */}
        <div className="si-sky-glow" />

        <div className="si-fade" />
      </section>

      {/* 핵심 기능 3가지: 밝은 노란 배경(도로 중앙선·표지판 색) 위 흰 카드 */}
      <section className="si-features">
        <div className="si-features-inner">
          <h2>
            <strong>에블리가 하는 일</strong>
          </h2>

          <div className="si-cards">
            <article className="si-card">
              <h3>블랙박스 영상 분석</h3>
              <div className="si-card-visual" aria-hidden="true">
                {/* 블랙박스 화면 + 충돌 전후 타임라인 */}
                <svg className="si-visual-cam" viewBox="0 0 200 132">
                  <rect x="20" y="6" width="160" height="92" rx="8" fill="#22242c" />
                  <path d="M92 26 L108 26 L156 98 L44 98 Z" fill="#3a3d48" />
                  <path d="M99.2 34h1.6v8h-1.6zM98.8 50h2.4v12h-2.4zM98.2 72h3.6v18h-3.6z" fill="#f2cc47" />
                  <rect x="112" y="52" width="26" height="16" rx="3" fill="#5a5f70" />
                  <rect x="114" y="62" width="5" height="3" rx="1" fill="#ff5a4a" />
                  <rect x="131" y="62" width="5" height="3" rx="1" fill="#ff5a4a" />
                  <circle cx="32" cy="18" r="3" fill="#ff5a4a" />
                  <text x="39" y="21" fontSize="8" fontWeight="700" fill="#fff">REC</text>
                  <line x1="28" y1="116" x2="172" y2="116" stroke="#cfd0d6" strokeWidth="2" />
                  {[
                    [36, "-5초"],
                    [82, "-3초"],
                    [128, "-1초"],
                  ].map(([x, t]) => (
                    <g key={t}>
                      <circle cx={x} cy="116" r="4" fill="#fff" stroke="#9a9ca6" strokeWidth="2" />
                      <text x={x} y="130" fontSize="8" textAnchor="middle" fill="#7a7c86">
                        {t}
                      </text>
                    </g>
                  ))}
                  <circle cx="168" cy="116" r="5" fill="#ff5a4a" />
                  <text x="168" y="130" fontSize="8" fontWeight="700" textAnchor="middle" fill="#e2463a">
                    충돌
                  </text>
                </svg>
              </div>
              <p className="si-card-desc">
                영상에서 사고 유형과 충돌 시점을 파악하고,
                <br />
                충돌 전후 주요 장면을 타임라인으로 보여줍니다.
              </p>
            </article>

            <article className="si-card">
              <h3>예상 과실비율과 판단 근거</h3>
              <div className="si-card-visual" aria-hidden="true">
                {/* 예상 과실비율 카드 */}
                <div className="si-mini si-ratio">
                  <span className="si-ratio-label">내 차 : 상대 차 (예시)</span>
                  <strong className="si-ratio-value">20 : 80</strong>
                  <div className="si-ratio-bar">
                    <span style={{ width: "20%" }} />
                    <span style={{ width: "80%" }} />
                  </div>
                  <span className="si-ratio-source">과실 인정 기준 · 출처 표시</span>
                </div>
              </div>
              <p className="si-card-desc">
                사고 유형에 해당하는 예상 과실비율과,
                <br />
                적용된 과실 인정 기준을 출처와 함께 보여줍니다.
              </p>
            </article>

            <article className="si-card">
              <h3>유사 사고 기준과 판례</h3>
              <div className="si-card-visual" aria-hidden="true">
                {/* 판례 문서 + 체크 목록 */}
                <div className="si-mini si-doc">
                  <span className="si-doc-tag">판례</span>
                  <span className="si-doc-line" />
                  <span className="si-doc-line short" />
                  <ul className="si-check">
                    <li>비슷한 판례 검색</li>
                    <li>공통점·차이점 비교</li>
                    <li>모든 근거에 출처</li>
                  </ul>
                </div>
              </div>
              <p className="si-card-desc">
                내 사고와 비슷한 판례를 찾아,
                <br />
                공통점과 차이점을 쉬운 말로 비교해 드립니다.
              </p>
            </article>
          </div>

          {/* 기능 소개를 다 본 뒤 바로 시작할 수 있게 */}
          <div className="si-cta-bar">
            <p className="si-cta-text">
              내 사고의 과실비율이 궁금하다면?
              <strong>블랙박스 영상으로 바로 확인해 보세요.</strong>
            </p>
            <div className="si-cta-buttons">
              <button className="si-btn si-btn-accent" onClick={() => navigate("/upload-test")}>
                블랙박스 영상 분석하기
                <span className="si-btn-arrow" aria-hidden="true">›</span>
              </button>
              <button className="si-btn si-btn-dark" onClick={() => navigate("/law")}>
                유사 판례 찾아보기
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
