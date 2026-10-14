/* ---------- 도로 · 가드레일 · 가로등 ----------
 * 고정된 도로 면(아스팔트, 차선, 가드레일)과, 매 프레임 다가오는 부분(점선, 지주, 다리 난간 기둥, 가로등)을 만든다. */
import {
  CAM_H,
  FOCAL,
  Z_START,
  Z_FAR,
  ROAD_HALF,
  EDGE_X,
  CENTER_X,
  LANE_X,
  LINE_W,
  DASH_LEN,
  DASH_PERIOD,
  DASH_MAX_Z,
  TRACK,
  project,
  pathOf,
  strip,
  n,
  box,
} from "./projection";
import { BRIDGE_RAIL_X, BRIDGE_RAIL_H, BRIDGE_POST_PERIOD, BRIDGE_POST_MAX_Z, FAR_BRIDGE_Z } from "./bridgeSea";

export const ROAD = strip(0, ROAD_HALF * 2, Z_START, Z_FAR);
export const SHOULDERS = [-1, 1].map((s) => strip(s * (EDGE_X + ROAD_HALF) / 2, ROAD_HALF - EDGE_X, Z_START, Z_FAR)).join("");
export const EDGES = [-EDGE_X, EDGE_X].map((x) => strip(x, LINE_W * 1.5, Z_START, Z_FAR)).join("");
export const CENTER = [-CENTER_X, CENTER_X].map((x) => strip(x, LINE_W, Z_START, Z_FAR)).join("");
// 차로마다 바퀴가 지나는 자리가 살짝 어둡게 닳은 자국
export const WEAR = [-5.2, -1.75, 1.75, 5.2]
  .flatMap((c) => [c - 0.85, c + 0.85])
  .map((x) => strip(x, 0.55, Z_START, Z_FAR))
  .join("");

const RAIL_X = [-8.2, 8.2];
const RAIL_POST_PERIOD = 4;
const REFLECTOR_PERIOD = 16; // TRACK과 RAIL_POST_PERIOD의 배수 관계 유지
const RAIL_POST_MAX_Z = 220;
const LAMP_MAX_Z = 480; // 멀리까지 그려서 다리를 따라 가로등이 이어져 보이게

// 양쪽으로 끝없이 이어지는 가드레일: 어두운 금속 판 + 위 가장자리 반사광 + 가운데 홈
const railStrip = (h1, h2) =>
  RAIL_X.map((x) => pathOf([project(x, Z_START, h1), project(x, Z_START, h2), project(x, Z_FAR, h2), project(x, Z_FAR, h1)])).join("");
export const RAIL_BODY = railStrip(0.6, 0.78);
export const RAIL_GROOVE = railStrip(0.68, 0.7);
export const RAIL_EDGE = railStrip(0.78, 0.8);

// 가로등: [바닥에 떨어진 빛, 기둥 + 도로 쪽 팔 + 은은한 주황 불빛]
function drawLamp(o, z) {
  const x = o.side * o.x;
  const armX = o.side * (o.x - 1.8);
  const [ax1, ay1] = project(x, z, o.h);
  const [ax2, ay2] = project(armX, z, o.h - 0.1);
  const [gx, gy] = project(armX, z, o.h - 0.25);
  // 바닥 빛은 등 바로 아래보다 조금 도로 안쪽에 중심을 둬서 차로를 넓게 비춤
  const [px, py] = project(o.side * (o.x - 3.2), z);
  const glow = (FOCAL * 3.9) / z;
  const pool = (FOCAL * 7.5) / z;
  const fade = n(Math.max(0.45, 1 - (z - 20) / 400));
  return [
    `<ellipse cx="${n(px)}" cy="${n(py)}" rx="${n(pool)}" ry="${n((pool * CAM_H) / z + 1)}" fill="url(#si-pool-warm)" opacity="${fade}"/>`,
    `<path d="${box(x, 0.18, z, 0, o.h)}" fill="#161c34"/>` +
    `<line x1="${n(ax1)}" y1="${n(ay1)}" x2="${n(ax2)}" y2="${n(ay2)}" stroke="#161c34" stroke-width="${n(Math.max((FOCAL * 0.12) / z, 0.6))}"/>` +
    `<circle cx="${n(gx)}" cy="${n(gy)}" r="${n(glow)}" fill="url(#si-lamp-warm)" opacity="${fade}"/>`,
  ];
}

// 가로등은 몇 개만, 양쪽 따로 넉넉한 간격으로
function makeLamps() {
  const rand = (a, b) => a + Math.random() * (b - a);
  const lamps = [];
  for (const side of [-1, 1]) {
    for (let z = rand(10, 60); z < TRACK - 40; z += rand(70, 130)) {
      lamps.push({ side, z, x: rand(8.6, 8.85), h: rand(8.5, 9.2) }); // 가드레일과 다리 난간 사이
    }
  }
  return lamps;
}
const LAMPS = makeLamps();

// 이동 거리 travel(m)에 맞춰 다가오는 부분들을 SVG 문자열로
export function movingParts(travel) {
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

  // 다리 바깥 난간 기둥(2.5m 간격). 먼 기둥(farBridgePosts)은 지평선 안개 위에 따로 밝게 그림
  let bridgePosts = "";
  let farBridgePosts = "";
  const bpOff = travel % BRIDGE_POST_PERIOD;
  for (let z = Z_START + BRIDGE_POST_PERIOD - bpOff; z < BRIDGE_POST_MAX_Z; z += BRIDGE_POST_PERIOD) {
    for (const x of BRIDGE_RAIL_X) {
      if (z < FAR_BRIDGE_Z) bridgePosts += box(x, 0.06, z, 0, BRIDGE_RAIL_H);
      else farBridgePosts += box(x, 0.12, z, 0, BRIDGE_RAIL_H); // 멀리서도 보이게 조금 두껍게
    }
  }

  // 가로등: 먼 것부터 그려야 가까운 것이 위에 덮임. 바닥 빛은 다리 위에만 보이게 따로 모음
  const drawn = LAMPS.map((o) => [Z_START + ((((o.z - travel) % TRACK) + TRACK) % TRACK), o])
    .filter(([z]) => z < LAMP_MAX_Z)
    .sort((a, b) => b[0] - a[0])
    .map(([z, o]) => drawLamp(o, z));
  const lampPools = drawn.map(([pool]) => pool).join("");
  const lamps = drawn.map(([, body]) => body).join("");
  // 바다를 비출 가로등 위치 (가까이 지나갈수록 강하게)
  const litLamps = LAMPS.map((o) => {
    const z = Z_START + ((((o.z - travel) % TRACK) + TRACK) % TRACK);
    return { x: o.side * o.x, z, fade: Math.max(0, Math.min(1, 1 - (z - 60) / 260)) };
  }).filter((l) => l.fade > 0);

  return { dashes, posts, reflectors, bridgePosts, farBridgePosts, lampPools, lamps, litLamps };
}
