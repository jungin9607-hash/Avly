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
            <stop offset="0" stopColor="#1f2d58" />
            <stop offset="0.05" stopColor="#16224a" />
            <stop offset="0.22" stopColor="#101a3a" />
            <stop offset="0.55" stopColor="#0a1128" />
            <stop offset="1" stopColor="#050914" />
          </linearGradient>
          {/* 다리 바깥 난간 기둥: 가로등 빛을 받은 밝은 금속. 멀수록 안개 색 */}
          <linearGradient id="si-bridge-post" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="500">
            <stop offset="0" stopColor="#4f6290" />
            <stop offset="0.35" stopColor="#7484a6" />
            <stop offset="1" stopColor="#98a3bd" />
          </linearGradient>
          {/* 지평선 쪽 다리 난간·기둥: 가로등 빛을 받아 안개 속에서도 은은하게 보이는 밝은 회청색 */}
          {/* 아래(가까운 쪽, 약 120m)에서는 투명해서 원래 난간과 자연스럽게 이어짐 */}
          <linearGradient id="si-bridge-far" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="44">
            <stop offset="0" stopColor="#cdd8f2" stopOpacity="1" />
            <stop offset="0.5" stopColor="#b6c4e6" stopOpacity="0.85" />
            <stop offset="1" stopColor="#a3b0cf" stopOpacity="0" />
          </linearGradient>
          {/* 가로등 빛이 바다에 퍼진 모습 */}
          <radialGradient id="si-sea-glow">
            <stop offset="0" stopColor="#ffc98a" stopOpacity="0.28" />
            <stop offset="0.45" stopColor="#c9a08a" stopOpacity="0.11" />
            <stop offset="1" stopColor="#8fa3d6" stopOpacity="0" />
          </radialGradient>
          {/* 다리 상판(보도): 멀수록 안개 색 */}
          <linearGradient id="si-deck" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="500">
            <stop offset="0" stopColor="#2e3a5e" />
            <stop offset="0.3" stopColor="#1f2433" />
            <stop offset="1" stopColor="#13161e" />
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
            <stop offset="0" stopColor="#3f4d6e" />
            <stop offset="0.35" stopColor="#454c60" />
            <stop offset="1" stopColor="#5a6072" />
          </linearGradient>
          {/* 레일 위 가장자리에만 전조등 반사광 */}
          <linearGradient id="si-rail-edge" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="500">
            <stop offset="0" stopColor="#5f6f96" />
            <stop offset="0.4" stopColor="#8a92a8" />
            <stop offset="1" stopColor="#d2d7e4" />
          </linearGradient>
          <linearGradient id="si-rail-post" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="500">
            <stop offset="0" stopColor="#1f2d58" />
            <stop offset="1" stopColor="#20253a" />
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
          {/* 다리 가로등 등갓 아래로 떨어지는 빛 기둥: 위는 은은하게 밝고 아래로 갈수록 사라짐 */}
          <linearGradient id="si-lamp-cone" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#ffd08a" stopOpacity="0.3" />
            <stop offset="0.5" stopColor="#ffd08a" stopOpacity="0.1" />
            <stop offset="1" stopColor="#ffd08a" stopOpacity="0" />
          </linearGradient>
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
            <stop offset="0" stopColor="#1f2d58" stopOpacity="1" />
            <stop offset="0.3" stopColor="#1f2d58" stopOpacity="0.4" />
            <stop offset="1" stopColor="#1f2d58" stopOpacity="0" />
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
        <path d={DECK_LIP} fill="#3a4870" />
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

        {/* 다리 가로등 (가드레일 뒤쪽): 양쪽 난간 위에 같은 간격으로 마주 보고, 멀리까지 불빛이 줄지어 이어짐 */}
        <g ref={lampsRef} />

        {/* 양쪽 가드레일: 지주 + 금속 판(가운데 홈, 위 가장자리 반사광) + 작은 반사판 */}
        <path ref={postsRef} fill="url(#si-rail-post)" />
        <path d={RAIL_BODY} fill="url(#si-rail)" />
        <path d={RAIL_GROOVE} fill="#12141f" opacity="0.55" />
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
          <ellipse key={i} cx={g.x} cy="30" rx={g.rx} ry="1.6" fill="#ffc27a" opacity="0.09" />
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

        {/* 지평선을 가로지르는 먼 다리 (도시 불빛 앞): 교각 → 케이블 → 주탑 → 상판 → 상판 가로등 줄 */}
        <g className="si-far-bridge">
          {/* 교각: 상판 아래에서 바다 속까지 굵게 내려가고, 물 위에는 흐릿한 반사 → 다리가 떠 보이지 않게 */}
          {skyline.farBridge.piers.map((x) => (
            <g key={x}>
              <line x1={x} x2={x} y1={skyline.farBridge.deckY + 0.9} y2="32.6" stroke="#8a9bc4" strokeWidth="1.3" opacity="0.8" />
              <line x1={x} x2={x} y1="32.6" y2="35.4" stroke="#8a9bc4" strokeWidth="1.1" opacity="0.22" />
            </g>
          ))}
          {skyline.farBridge.pylons.map((p) =>
            p.cables.map((c, i) => (
              <line
                key={`${p.x}-${i}`}
                x1={p.x}
                y1={c.y1}
                x2={c.x2}
                y2={skyline.farBridge.deckY}
                stroke="#a9b8dc"
                strokeWidth="0.25"
                opacity="0.55"
              />
            ))
          )}
          {skyline.farBridge.pylons.map((p) => (
            <line key={p.x} x1={p.x} x2={p.x} y1={p.top} y2="32.6" stroke="#a9b8dc" strokeWidth="1.2" opacity="0.85" />
          ))}
          {/* 상판: 밝은 윗면 + 아래쪽 어두운 두께 */}
          <rect x="0" y={skyline.farBridge.deckY} width="1440" height="0.6" fill="#a9b8dc" opacity="0.7" />
          <rect x="0" y={skyline.farBridge.deckY + 0.6} width="1440" height="0.4" fill="#5d6d96" opacity="0.7" />
          {skyline.farBridge.deckLamps.map((l, i) => (
            <circle key={i} cx={l.x} cy={skyline.farBridge.deckY - 0.35} r="0.45" fill={l.color} opacity={l.o} />
          ))}
        </g>
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
