import { useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { useNavigate } from "react-router-dom";
import TopNav from "../../components/common/TopNav";
import "./Intro.css";

gsap.registerPlugin(ScrollTrigger, useGSAP);

/* ---------- 도로 원근 투영 ----------
 * 실제 도로 치수(m)를 화면 좌표로 투영한다.
 * 카메라 높이 CAM_H, 화면 아래 끝(y=500)이 Z_NEAR 거리, 지평선이 y=0.
 * 멀어질수록 차선 폭·점선 길이·간격이 함께 줄어들어 원근감이 생긴다. */
const VP_X = 720;
const CAM_H = 3.6;
const Z_NEAR = 6;
const FOCAL = (500 * Z_NEAR) / CAM_H;
const Z_START = 4; // 화면 아래 바깥에서부터 그림
const Z_FAR = 800;

const ROAD_HALF = 7.6; // 갓길 포함 도로 반폭
const EDGE_X = 6.9; // 바깥 흰 실선
const CENTER_X = 0.13; // 노란 중앙 이중선
const LANE_X = [-3.5, 3.5]; // 흰 점선
const LINE_W = 0.12;

const DASH_LEN = 3; // 점선 길이 3m, 간격 5m
const DASH_PERIOD = 8;
const DASH_MAX_Z = 260;
const TRACK = 800; // 길가 풍경이 반복되는 거리(m). DASH_PERIOD의 배수
const SPEED = 20; // m/s

const project = (x, z, h = 0) => [VP_X + (FOCAL * x) / z, (FOCAL * (CAM_H - h)) / z];
const pathOf = (pts) => "M" + pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join("L") + "Z";
const strip = (x, w, z1, z2) =>
  pathOf([project(x - w / 2, z1), project(x + w / 2, z1), project(x + w / 2, z2), project(x - w / 2, z2)]);

const ROAD = strip(0, ROAD_HALF * 2, Z_START, Z_FAR);
const SHOULDERS = [-1, 1].map((s) => strip(s * (EDGE_X + ROAD_HALF) / 2, ROAD_HALF - EDGE_X, Z_START, Z_FAR)).join("");
const EDGES = [-EDGE_X, EDGE_X].map((x) => strip(x, LINE_W * 1.5, Z_START, Z_FAR)).join("");
const CENTER = [-CENTER_X, CENTER_X].map((x) => strip(x, LINE_W, Z_START, Z_FAR)).join("");
// 차로마다 바퀴가 지나는 자리가 살짝 어둡게 닳은 자국
const WEAR = [-5.2, -1.75, 1.75, 5.2]
  .flatMap((c) => [c - 0.85, c + 0.85])
  .map((x) => strip(x, 0.55, Z_START, Z_FAR))
  .join("");

function movingParts(travel) {
  let dashes = "";
  const dashOff = travel % DASH_PERIOD;
  for (let z = Z_START - dashOff; z < DASH_MAX_Z; z += DASH_PERIOD) {
    if (z + DASH_LEN <= Z_START) continue;
    for (const x of LANE_X) dashes += strip(x, LINE_W, Math.max(z, Z_START), z + DASH_LEN);
  }

  // 가드레일 지주(4m 간격)와 그 위 반사판(16m 간격)
  let posts = "";
  let reflectors = "";
  const postOff = travel % RAIL_POST_PERIOD;
  for (let z = Z_START + RAIL_POST_PERIOD - postOff; z < RAIL_POST_MAX_Z; z += RAIL_POST_PERIOD) {
    const lit = Math.round(z + travel) % REFLECTOR_PERIOD === 0;
    for (const x of RAIL_X) {
      posts += box(x, 0.09, z, 0, 0.78);
      if (lit) reflectors += box(x, 0.07, z, 0.66, 0.71);
    }
  }

  // 가로등: 먼 것부터 그려야 가까운 것이 위에 덮임
  const lamps = LAMPS.map((o) => [Z_START + ((((o.z - travel) % TRACK) + TRACK) % TRACK), o])
    .filter(([z]) => z < LAMP_MAX_Z)
    .sort((a, b) => b[0] - a[0])
    .map(([z, o]) => drawLamp(o, z))
    .join("");

  return { dashes, posts, reflectors, lamps };
}

/* ---------- 가드레일 · 가로등 ---------- */
const RAIL_X = [-8.2, 8.2];
const RAIL_POST_PERIOD = 4;
const REFLECTOR_PERIOD = 16; // TRACK과 RAIL_POST_PERIOD의 배수 관계 유지
const RAIL_POST_MAX_Z = 220;
const LAMP_MAX_Z = 320;

// 양쪽으로 끝없이 이어지는 가드레일: 어두운 금속 판 + 위 가장자리 반사광 + 가운데 홈
const railStrip = (h1, h2) =>
  RAIL_X.map((x) => pathOf([project(x, Z_START, h1), project(x, Z_START, h2), project(x, Z_FAR, h2), project(x, Z_FAR, h1)])).join("");
const RAIL_BODY = railStrip(0.6, 0.78);
const RAIL_GROOVE = railStrip(0.68, 0.7);
const RAIL_EDGE = railStrip(0.78, 0.8);

const n = (v) => v.toFixed(1);
const box = (x, w, z, h1, h2) => {
  const [x1, y1] = project(x - w / 2, z, h1);
  const [x2, y2] = project(x + w / 2, z, h2);
  return pathOf([[x1, y1], [Math.max(x2, x1 + 0.6), y1], [Math.max(x2, x1 + 0.6), y2], [x1, y2]]);
};

// 가로등: 기둥 + 도로 쪽 팔 + 은은한 주황 불빛 + 바닥에 떨어진 빛
function drawLamp(o, z) {
  const x = o.side * o.x;
  const armX = o.side * (o.x - 1.8);
  const [ax1, ay1] = project(x, z, o.h);
  const [ax2, ay2] = project(armX, z, o.h - 0.1);
  const [gx, gy] = project(armX, z, o.h - 0.25);
  const [px, py] = project(armX, z);
  const glow = (FOCAL * 2.8) / z;
  const pool = (FOCAL * 4) / z;
  const fade = n(Math.max(0.45, 1 - (z - 20) / 400));
  return (
    `<ellipse cx="${n(px)}" cy="${n(py)}" rx="${n(pool)}" ry="${n((pool * CAM_H) / z + 1)}" fill="url(#si-pool-warm)" opacity="${fade}"/>` +
    `<path d="${box(x, 0.18, z, 0, o.h)}" fill="#161c34"/>` +
    `<line x1="${n(ax1)}" y1="${n(ay1)}" x2="${n(ax2)}" y2="${n(ay2)}" stroke="#161c34" stroke-width="${n(Math.max((FOCAL * 0.12) / z, 0.6))}"/>` +
    `<circle cx="${n(gx)}" cy="${n(gy)}" r="${n(glow)}" fill="url(#si-lamp-warm)" opacity="${fade}"/>`
  );
}

// 가로등은 몇 개만, 양쪽 따로 넉넉한 간격으로
function makeLamps() {
  const rand = (a, b) => a + Math.random() * (b - a);
  const lamps = [];
  for (const side of [-1, 1]) {
    for (let z = rand(10, 60); z < TRACK - 40; z += rand(70, 130)) {
      lamps.push({ side, z, x: rand(9, 9.3), h: rand(8.5, 9.2) });
    }
  }
  return lamps;
}
const LAMPS = makeLamps();

// 아스팔트 질감용 노이즈 (한 번만 생성)
function makeNoise() {
  const size = 160;
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d");
  const img = ctx.createImageData(size, size);
  for (let i = 0; i < img.data.length; i += 4) {
    const v = Math.random() > 0.5 ? 255 : 0;
    img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
    img.data[i + 3] = Math.random() * 46;
  }
  ctx.putImageData(img, 0, 0);
  return c.toDataURL();
}

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
  const dashesRef = useRef(null);
  const postsRef = useRef(null);
  const reflectorsRef = useRef(null);
  const lampsRef = useRef(null);
  const [noise] = useState(makeNoise);
  const [stars] = useState(makeStars);

  useGSAP(
    () => {
      const motion = { travel: 0 };
      const draw = () => {
        const { dashes, posts, reflectors, lamps } = movingParts(motion.travel);
        dashesRef.current.setAttribute("d", dashes);
        postsRef.current.setAttribute("d", posts);
        reflectorsRef.current.setAttribute("d", reflectors);
        lampsRef.current.innerHTML = lamps;
      };
      draw();
      // 어둠 레이어는 화면 아래 바깥에서 대기
      gsap.set(".si-fade", { yPercent: 100 });

      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (reduce) return;

      // 차선과 가드레일·가로등이 계속 다가오는 느낌 (항상 재생)
      const drive = gsap.to(motion, {
        travel: TRACK,
        duration: TRACK / SPEED,
        ease: "none",
        repeat: -1,
        onUpdate: draw,
      });

      // 스크롤에 따라: 제목이 걷히고 → 가속하며 도로 속으로 들어가고 →
      // 아래에서 어둠이 차올라 기능 소개 배경과 이어짐
      gsap
        .timeline({
          defaults: { ease: "none" },
          scrollTrigger: {
            trigger: ".si-hero",
            start: "top top",
            end: "+=700",
            scrub: 1.2,
            pin: true,
          },
        })
        .to(".si-hero-text", { opacity: 0, y: -80, ease: "power1.in", duration: 0.45 }, 0)
        .to(".si-sky-glow", { opacity: 0, duration: 0.6 }, 0)
        .to(".si-stars", { y: -60, opacity: 0, duration: 0.7 }, 0)
        .to(".si-road", { scale: 2.4, ease: "sine.in", duration: 1 }, 0)
        .to(drive, { timeScale: 3, ease: "power1.in", duration: 1 }, 0)
        .to(".si-fade", { yPercent: 0, ease: "power1.inOut", duration: 0.7 }, 0.3);

      // 기능 소개: 제목과 카드가 스크롤에 맞춰 차례로 떠오름
      gsap.from([".si-features h2", ".si-card"], {
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
          <div className="si-actions">
            <button className="si-btn si-btn-solid si-btn-lg" onClick={() => navigate("/upload-test")}>
              블랙박스 영상 분석하기
              <span className="si-btn-arrow" aria-hidden="true">→</span>
            </button>
          </div>
        </div>

        <svg
          className="si-road"
          viewBox="0 0 1440 500"
          preserveAspectRatio="xMidYMin slice"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="si-ground" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#2a2640" />
              <stop offset="0.12" stopColor="#1a1a2c" />
              <stop offset="0.45" stopColor="#0d1328" />
              <stop offset="1" stopColor="#070a16" />
            </linearGradient>
            <linearGradient id="si-asphalt" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#283048" />
              <stop offset="0.3" stopColor="#181b24" />
              <stop offset="1" stopColor="#0e1015" />
            </linearGradient>
            {/* 차선 도료: 멀수록 어둡고, 가까울수록 전조등을 받아 밝게 */}
            <linearGradient id="si-paint-white" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="500">
              <stop offset="0" stopColor="#6c7290" />
              <stop offset="0.5" stopColor="#c9cbd8" />
              <stop offset="1" stopColor="#f6f7fb" />
            </linearGradient>
            <linearGradient id="si-paint-yellow" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="500">
              <stop offset="0" stopColor="#7d6a3a" />
              <stop offset="0.5" stopColor="#d4a935" />
              <stop offset="1" stopColor="#f5c84a" />
            </linearGradient>
            {/* 가드레일: 무광 금속. 멀수록 안개 색, 가까울수록 어두운 회색 */}
            <linearGradient id="si-rail" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="500">
              <stop offset="0" stopColor="#2a2640" />
              <stop offset="0.35" stopColor="#3e3c4c" />
              <stop offset="1" stopColor="#5e5d6c" />
            </linearGradient>
            {/* 레일 위 가장자리에만 전조등 반사광 */}
            <linearGradient id="si-rail-edge" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="500">
              <stop offset="0" stopColor="#3a3650" />
              <stop offset="0.4" stopColor="#8c8a9a" />
              <stop offset="1" stopColor="#d4d3dd" />
            </linearGradient>
            <linearGradient id="si-rail-post" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="500">
              <stop offset="0" stopColor="#2a2640" />
              <stop offset="1" stopColor="#24232e" />
            </linearGradient>
            {/* 가로등 불빛과 바닥에 떨어진 빛 */}
            <radialGradient id="si-lamp-warm">
              <stop offset="0" stopColor="#fff2d6" stopOpacity="1" />
              <stop offset="0.12" stopColor="#ffc773" stopOpacity="1" />
              <stop offset="0.4" stopColor="#ffb05a" stopOpacity="0.34" />
              <stop offset="1" stopColor="#ffb05a" stopOpacity="0" />
            </radialGradient>
            <radialGradient id="si-pool-warm">
              <stop offset="0" stopColor="#ffc773" stopOpacity="0.38" />
              <stop offset="1" stopColor="#ffc773" stopOpacity="0" />
            </radialGradient>
            <radialGradient id="si-headlight">
              <stop offset="0" stopColor="#fff1c9" stopOpacity="0.2" />
              <stop offset="0.6" stopColor="#fff1c9" stopOpacity="0.06" />
              <stop offset="1" stopColor="#fff1c9" stopOpacity="0" />
            </radialGradient>
            {/* 지평선 쪽 안개: 하늘색과 이어지게 */}
            <linearGradient id="si-haze" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#2a2640" stopOpacity="1" />
              <stop offset="0.3" stopColor="#2a2640" stopOpacity="0.55" />
              <stop offset="1" stopColor="#2a2640" stopOpacity="0" />
            </linearGradient>
            <pattern id="si-grain" width="160" height="160" patternUnits="userSpaceOnUse">
              <image href={noise} width="160" height="160" />
            </pattern>
          </defs>

          {/* 땅 → 아스팔트 → 갓길 → 바퀴 자국 → 질감 */}
          <rect width="1440" height="500" fill="url(#si-ground)" />
          <path d={ROAD} fill="url(#si-asphalt)" />
          <path d={SHOULDERS} fill="#0b0b10" opacity="0.6" />
          <path d={WEAR} fill="#000" opacity="0.22" />
          <path d={ROAD} fill="url(#si-grain)" />

          {/* 차선: 바깥 흰 실선, 노란 중앙 이중선, 흰 점선 */}
          <path d={EDGES} fill="url(#si-paint-white)" />
          <path d={CENTER} fill="url(#si-paint-yellow)" />
          <path ref={dashesRef} fill="url(#si-paint-white)" />

          {/* 가로등 (가드레일 뒤쪽) */}
          <g ref={lampsRef} />

          {/* 양쪽 가드레일: 지주 + 금속 판(가운데 홈, 위 가장자리 반사광) + 작은 반사판 */}
          <path ref={postsRef} fill="url(#si-rail-post)" />
          <path d={RAIL_BODY} fill="url(#si-rail)" />
          <path d={RAIL_GROOVE} fill="#14131c" opacity="0.55" />
          <path d={RAIL_EDGE} fill="url(#si-rail-edge)" />
          <path ref={reflectorsRef} fill="#e0a26c" opacity="0.6" />

          {/* 전조등 빛과 지평선 안개 */}
          <ellipse cx="720" cy="500" rx="900" ry="340" fill="url(#si-headlight)" />
          <rect width="1440" height="150" fill="url(#si-haze)" />
        </svg>

        {/* 지평선의 호박색 빛 (먼 도로까지 은은하게 물듦) */}
        <div className="si-sky-glow" />

        <div className="si-fade" />
      </section>

      {/* 핵심 기능 3가지 */}
      <section className="si-features">
        <h2>에블리가 하는 일</h2>
        <div className="si-cards">
          <article className="si-card">
            <h3>블랙박스 영상 분석</h3>
            <p>영상에서 사고 유형과 충돌 시점을 파악하고, 충돌 전후 주요 장면을 타임라인으로 보여줍니다.</p>
            <ol className="si-timeline">
              <li>-5초</li>
              <li>-3초</li>
              <li>-1초</li>
              <li className="hit">충돌</li>
            </ol>
          </article>

          <article className="si-card">
            <h3>예상 과실비율과 판단 근거</h3>
            <p>사고 유형에 해당하는 예상 과실비율과, 적용된 과실 인정 기준을 출처와 함께 보여줍니다.</p>
            <div className="si-ratio">
              <div className="si-ratio-head">
                <span>내 차 · 상대 차 (예시)</span>
                <strong>20 : 80</strong>
              </div>
              <div className="si-ratio-bar">
                <span style={{ width: "20%" }} />
                <span style={{ width: "80%" }} />
              </div>
            </div>
          </article>

          <article className="si-card">
            <h3>유사 사고 기준과 판례</h3>
            <p>내 사고와 비슷한 판례를 찾아, 공통점과 차이점을 쉬운 말로 비교해 드립니다.</p>
            <ul className="si-check">
              <li>내 사고와 비슷한 판례 검색</li>
              <li>공통점과 차이점 비교</li>
              <li>모든 근거에 출처 표시</li>
            </ul>
          </article>
        </div>
      </section>
    </div>
  );
}
