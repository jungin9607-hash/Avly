import { useRef, useState } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { TRACK, SPEED } from "./projection";
import {
  ROAD,
  SHOULDERS,
  EDGES,
  CENTER,
  WEAR,
  RAIL_BODY,
  RAIL_GROOVE,
  RAIL_EDGE,
  movingParts,
} from "./road";
import {
  DECK,
  DECK_LIP,
  BRIDGE_RAILS,
  FAR_BRIDGE_RAILS,
  FAR_DECK_LIP,
  drawWaves,
  drawSeaGlows,
  makeSkyline,
} from "./bridgeSea";
import { drawCars } from "./cars";
import { ASPHALT_W, ASPHALT_H, makeAsphalt, paintAsphalt } from "./asphalt";

gsap.registerPlugin(useGSAP);

/* 밤바다 위 다리를 달리는 도로 장면 (도로 SVG + 먼 해안 도시 불빛).
 * 매 프레임 다가오는 부분을 다시 그린다. 계속 달리는 트윈은 driveRef로 넘겨서,
 * 페이지(Intro)의 스크롤 효과가 속도(timeScale)를 조절할 수 있게 한다. */
export default function RoadScene({ driveRef }) {
  const dashesRef = useRef(null);
  const postsRef = useRef(null);
  const reflectorsRef = useRef(null);
  const lampsRef = useRef(null);
  const carsRef = useRef(null);
  const asphaltRef = useRef(null);
  const bridgePostsRef = useRef(null);
  const farBridgePostsRef = useRef(null);
  const lampPoolsRef = useRef(null);
  const wavesARef = useRef(null);
  const wavesBRef = useRef(null);
  const wavesLitRef = useRef(null);
  const wavesLitStrongRef = useRef(null);
  const seaGlowsRef = useRef(null);
  const [skyline] = useState(makeSkyline);

  useGSAP(() => {
    const motion = { travel: 0 };
    // travel은 TRACK마다 0으로 돌아가므로, 차들은 끊김 없이 누적한 거리로 움직임
    let lastTravel = 0;
    let dist = 0;

    const asphalt = asphaltRef.current.getContext("2d");
    const asphaltImg = asphalt.createImageData(ASPHALT_W, ASPHALT_H);
    const asphaltPixels = new Uint32Array(asphaltImg.data.buffer);
    const asphaltTex = makeAsphalt();

    const draw = () => {
      let step = motion.travel - lastTravel;
      if (step < 0) step += TRACK;
      lastTravel = motion.travel;
      dist += step;

      const { dashes, posts, reflectors, bridgePosts, farBridgePosts, lampPools, lamps, litLamps } = movingParts(motion.travel);
      const [wavesA, wavesB, wavesLit, wavesLitStrong] = drawWaves(dist, litLamps);
      wavesARef.current.setAttribute("d", wavesA);
      wavesBRef.current.setAttribute("d", wavesB);
      wavesLitRef.current.setAttribute("d", wavesLit);
      wavesLitStrongRef.current.setAttribute("d", wavesLitStrong);
      seaGlowsRef.current.innerHTML = drawSeaGlows(litLamps);
      bridgePostsRef.current.setAttribute("d", bridgePosts);
      farBridgePostsRef.current.setAttribute("d", farBridgePosts);
      lampPoolsRef.current.innerHTML = lampPools;
      dashesRef.current.setAttribute("d", dashes);
      postsRef.current.setAttribute("d", posts);
      reflectorsRef.current.setAttribute("d", reflectors);
      lampsRef.current.innerHTML = lamps;
      carsRef.current.innerHTML = drawCars(dist);
      paintAsphalt(asphaltPixels, asphaltTex, dist);
      asphalt.putImageData(asphaltImg, 0, 0);
    };
    draw();

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;

    // 차선과 가드레일·가로등이 계속 다가오는 느낌 (항상 재생)
    driveRef.current = gsap.to(motion, {
      travel: TRACK,
      duration: TRACK / SPEED,
      ease: "none",
      repeat: -1,
      onUpdate: draw,
    });
  });

  return (
    <>
      <svg
        className="si-road"
        viewBox="0 0 1440 500"
        preserveAspectRatio="xMidYMin slice"
        aria-hidden="true"
      >
        <defs>
          {/* 밤바다: 지평선은 안개 색, 가까울수록 깊은 남색 */}
          <linearGradient id="si-sea" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="500">
            <stop offset="0" stopColor="#2a2640" />
            <stop offset="0.05" stopColor="#1b1c33" />
            <stop offset="0.22" stopColor="#12172f" />
            <stop offset="0.55" stopColor="#0a0e1f" />
            <stop offset="1" stopColor="#05070f" />
          </linearGradient>
          {/* 다리 바깥 난간 기둥: 가로등 빛을 받은 밝은 금속. 멀수록 안개 색 */}
          <linearGradient id="si-bridge-post" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="500">
            <stop offset="0" stopColor="#57527a" />
            <stop offset="0.35" stopColor="#77748c" />
            <stop offset="1" stopColor="#9a98a8" />
          </linearGradient>
          {/* 지평선 쪽 다리 난간·기둥: 가로등 빛을 받아 안개 속에서도 은은하게 보이는 밝은 회보라 */}
          {/* 아래(가까운 쪽, 약 120m)에서는 투명해서 원래 난간과 자연스럽게 이어짐 */}
          <linearGradient id="si-bridge-far" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="44">
            <stop offset="0" stopColor="#d2cee9" stopOpacity="1" />
            <stop offset="0.5" stopColor="#bcb8d8" stopOpacity="0.85" />
            <stop offset="1" stopColor="#a9a6bf" stopOpacity="0" />
          </linearGradient>
          {/* 가로등 빛이 바다에 퍼진 모습 */}
          <radialGradient id="si-sea-glow">
            <stop offset="0" stopColor="#ffc98a" stopOpacity="0.28" />
            <stop offset="0.45" stopColor="#c9a08a" stopOpacity="0.11" />
            <stop offset="1" stopColor="#8fa3d6" stopOpacity="0" />
          </radialGradient>
          {/* 다리 상판(보도): 멀수록 안개 색 */}
          <linearGradient id="si-deck" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="500">
            <stop offset="0" stopColor="#3a3552" />
            <stop offset="0.3" stopColor="#23222e" />
            <stop offset="1" stopColor="#15151b" />
          </linearGradient>
          {/* 가로등 바닥 빛은 도로와 다리 상판 위에만 */}
          <clipPath id="si-deck-clip">
            <path d={ROAD + DECK} />
          </clipPath>
          <linearGradient id="si-asphalt" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#2a2e40" />
            <stop offset="0.3" stopColor="#1a1c23" />
            <stop offset="1" stopColor="#111216" />
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
            <stop offset="0" stopColor="#4a4563" />
            <stop offset="0.35" stopColor="#4a4858" />
            <stop offset="1" stopColor="#5e5d6c" />
          </linearGradient>
          {/* 레일 위 가장자리에만 전조등 반사광 */}
          <linearGradient id="si-rail-edge" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="500">
            <stop offset="0" stopColor="#6a6585" />
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
            <stop offset="0.4" stopColor="#ffb05a" stopOpacity="0.3" />
            <stop offset="0.75" stopColor="#ffb05a" stopOpacity="0.06" />
            <stop offset="1" stopColor="#ffb05a" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="si-pool-warm">
            {/* 중심은 또렷하게, 가장자리는 빨리 어두워져 뿌옇게 번지지 않게 */}
            <stop offset="0" stopColor="#ffc773" stopOpacity="0.5" />
            <stop offset="0.35" stopColor="#ffc773" stopOpacity="0.32" />
            <stop offset="0.7" stopColor="#ffc773" stopOpacity="0.07" />
            <stop offset="1" stopColor="#ffc773" stopOpacity="0" />
          </radialGradient>
          {/* 다른 차의 미등·전조등과 전조등이 비춘 도로 */}
          <radialGradient id="si-tail-glow">
            <stop offset="0" stopColor="#ff6a5a" stopOpacity="0.9" />
            <stop offset="0.3" stopColor="#ff3b3b" stopOpacity="0.35" />
            <stop offset="1" stopColor="#ff3b3b" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="si-head-glow">
            <stop offset="0" stopColor="#ffffff" stopOpacity="1" />
            <stop offset="0.15" stopColor="#fff1c9" stopOpacity="0.8" />
            <stop offset="0.45" stopColor="#fff1c9" stopOpacity="0.2" />
            <stop offset="1" stopColor="#fff1c9" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="si-car-beam">
            <stop offset="0" stopColor="#fff1c9" stopOpacity="0.28" />
            <stop offset="1" stopColor="#fff1c9" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="si-headlight">
            <stop offset="0" stopColor="#fff1c9" stopOpacity="0.2" />
            <stop offset="0.6" stopColor="#fff1c9" stopOpacity="0.06" />
            <stop offset="1" stopColor="#fff1c9" stopOpacity="0" />
          </radialGradient>
          {/* 지평선 쪽 안개: 하늘색과 이어지게 */}
          <linearGradient id="si-haze" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#2a2640" stopOpacity="1" />
            <stop offset="0.3" stopColor="#2a2640" stopOpacity="0.4" />
            <stop offset="1" stopColor="#2a2640" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* 밤바다 → 잔물결 → 다리 상판 → 아스팔트 → 질감(원근 투영, 함께 움직임) → 갓길 → 바퀴 자국 */}
        <rect width="1440" height="500" fill="url(#si-sea)" />
        {/* 잔물결 묶음(.si-sea-waves)과 아스팔트 질감(.si-asphalt-tex)은 스크롤로 도로 속에 들어갈 때
            확대·가속되면 자글거리므로 Intro의 스크롤 효과에서 흐려 없앰 */}
        <g className="si-sea-waves">
          <path ref={wavesARef} className="si-wave si-wave-a" fill="#a3b5e3" fillOpacity="0.28" />
          <path ref={wavesBRef} className="si-wave si-wave-b" fill="#a3b5e3" fillOpacity="0.28" />
          {/* 가로등이 지나가면 주변 바다가 밝아지고 물결이 빛을 받아 반짝임 */}
          <g ref={seaGlowsRef} />
          <path ref={wavesLitRef} className="si-wave si-wave-a" fill="#f0d2a8" fillOpacity="0.42" />
          <path ref={wavesLitStrongRef} className="si-wave si-wave-b" fill="#ffdcaa" fillOpacity="0.58" />
        </g>
        <path d={DECK} fill="url(#si-deck)" />
        <path d={DECK_LIP} fill="#45415c" />
        <path d={ROAD} fill="url(#si-asphalt)" />
        <foreignObject className="si-asphalt-tex" width="1440" height="500">
          <canvas
            ref={asphaltRef}
            width={ASPHALT_W}
            height={ASPHALT_H}
            style={{ display: "block", width: "100%", height: "100%" }}
          />
        </foreignObject>
        <path d={SHOULDERS} fill="#0b0b10" opacity="0.6" />
        <path d={WEAR} fill="#000" opacity="0.22" />

        {/* 차선: 바깥 흰 실선, 노란 중앙 이중선, 흰 점선 */}
        <path d={EDGES} fill="url(#si-paint-white)" />
        <path d={CENTER} fill="url(#si-paint-yellow)" />
        <path ref={dashesRef} fill="url(#si-paint-white)" />

        {/* 가로등이 도로·상판에 떨어뜨린 빛 */}
        <g ref={lampPoolsRef} clipPath="url(#si-deck-clip)" />

        {/* 다리 바깥 난간: 기둥 + 손잡이 + 중간 가로대 */}
        <path ref={bridgePostsRef} fill="url(#si-bridge-post)" />
        <path d={BRIDGE_RAILS} fill="url(#si-rail)" />

        {/* 가로등 (가드레일 뒤쪽) */}
        <g ref={lampsRef} />

        {/* 양쪽 가드레일: 지주 + 금속 판(가운데 홈, 위 가장자리 반사광) + 작은 반사판 */}
        <path ref={postsRef} fill="url(#si-rail-post)" />
        <path d={RAIL_BODY} fill="url(#si-rail)" />
        <path d={RAIL_GROOVE} fill="#14131c" opacity="0.55" />
        <path d={RAIL_EDGE} fill="url(#si-rail-edge)" />
        <path ref={reflectorsRef} fill="#e0a26c" opacity="0.6" />

        {/* 도로 위를 달리는 차들 */}
        <g ref={carsRef} />

        {/* 전조등 빛과 지평선 안개 */}
        <ellipse cx="720" cy="500" rx="900" ry="340" fill="url(#si-headlight)" />
        <rect width="1440" height="150" fill="url(#si-haze)" />

        {/* 지평선 쪽 다리: 안개에 묻히지 않게 상판 가장자리·난간·기둥을 밝게 한 번 더 (다리임을 알아보게) */}
        <g>
          <path d={FAR_DECK_LIP} fill="url(#si-bridge-far)" />
          <path d={FAR_BRIDGE_RAILS} fill="url(#si-bridge-far)" />
          <path ref={farBridgePostsRef} fill="url(#si-bridge-far)" />
        </g>
      </svg>

      {/* 먼 해안 도시 불빛과 바다에 비친 빛 (지평선 양옆에만) */}
      <svg className="si-skyline" viewBox="0 0 1440 60" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        {skyline.glows.map((g, i) => (
          <ellipse key={i} cx={g.x} cy="30" rx={g.rx} ry="1.6" fill="#ffc27a" opacity="0.18" />
        ))}
        {skyline.reflections.map((r, i) => (
          <line
            key={i}
            x1={r.x}
            x2={r.x}
            y1="30.8"
            y2={30.8 + r.len}
            stroke={r.color}
            strokeWidth="0.6"
            strokeDasharray="1.2 0.9"
            opacity={r.o}
          />
        ))}
        {skyline.lights.map((l, i) => (
          <circle key={i} cx={l.x} cy={l.y} r={l.r} fill={l.color} opacity={l.o} />
        ))}
        {skyline.beacons.map((b, i) => (
          <circle
            key={i}
            className="si-beacon"
            cx={b.x}
            cy={b.y}
            r="0.7"
            fill="#ff5a4a"
            style={{ animationDelay: `${b.delay}s` }}
          />
        ))}
      </svg>
    </>
  );
}
