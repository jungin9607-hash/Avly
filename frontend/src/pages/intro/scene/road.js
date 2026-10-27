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
const LAMP_MAX_Z = 760; // 지평선 가까이까지 그려서 다리를 따라 불빛이 줄지어 이어져 보이게

// 양쪽으로 끝없이 이어지는 가드레일: 어두운 금속 판 + 위 가장자리 반사광 + 가운데 홈
const railStrip = (h1, h2) =>
  RAIL_X.map((x) => pathOf([project(x, Z_START, h1), project(x, Z_START, h2), project(x, Z_FAR, h2), project(x, Z_FAR, h1)])).join("");
export const RAIL_BODY = railStrip(0.6, 0.78);
export const RAIL_GROOVE = railStrip(0.68, 0.7);
export const RAIL_EDGE = railStrip(0.78, 0.8);

// 다리 위 가로등: 양쪽 난간 위에 같은 간격으로 마주 보고 선 높은 기둥
//   위로 갈수록 가늘어지는 기둥 → 도로 쪽으로 휘어진 팔 → 납작한 등갓 → 아래로 퍼지는 빛 기둥
//   멀리 있는 등은 기둥 없이 불빛 점만 그려, 지평선까지 빛의 줄이 이어져 다리 길이가 느껴지게
const LAMP_PERIOD = 40; // 등 간격(m). TRACK의 약수라 반복 경계에서도 간격이 일정
const LAMP_X = 9.0; // 다리 바깥 난간(9.15) 바로 안쪽
const LAMP_H = 9.5; // 기둥 높이
const LAMP_REACH = 2.4; // 팔이 도로 쪽으로 뻗는 길이
const LAMP_DETAIL_Z = 260; // 이보다 먼 등은 불빛 점만

// 가로등 하나: [바닥에 떨어진 빛, 빛 기둥 + 기둥 + 팔 + 등갓 + 불빛]
function drawLamp(o, z) {
  const x = o.side * LAMP_X;
  const headX = o.side * (LAMP_X - LAMP_REACH); // 등갓 가운데
  const headH = LAMP_H + 0.35;
  const fade = n(Math.max(0.4, 1 - (z - 20) / 520));
  const [gx, gy] = project(headX, z, headH - 0.12);

  // 먼 등: 불빛 점만 (지평선까지 이어지는 빛의 줄)
  if (z > LAMP_DETAIL_Z) {
    const r = Math.max((FOCAL * 2.4) / z, 1.6);
    return ["", `<circle cx="${n(gx)}" cy="${n(gy)}" r="${n(r)}" fill="url(#si-lamp-warm)" opacity="${fade}"/>`];
  }

  // 바닥 빛: 등갓 바로 아래 차로를 넓게 비춤
  const [px, py] = project(headX - o.side * 0.6, z);
  const pool = (FOCAL * 7.5) / z;

  // 기둥: 아래는 굵고 위로 갈수록 가늘게 (0.26m → 0.12m)
  const [b1x, b1y] = project(x - 0.13, z, 0);
  const [b2x] = project(x + 0.13, z, 0);
  const [t1x, t1y] = project(x - 0.06, z, LAMP_H);
  const [t2x] = project(x + 0.06, z, LAMP_H);
  const pole = pathOf([[b1x, b1y], [Math.max(b2x, b1x + 0.6), b1y], [Math.max(t2x, t1x + 0.4), t1y], [t1x, t1y]]);

  // 팔: 기둥 끝에서 살짝 솟았다가 도로 쪽으로 휘어 내려와 등갓에 닿음
  const [ax, ay] = project(x, z, LAMP_H);
  const [cx, cy] = project(x - o.side * 0.5, z, LAMP_H + 0.75);
  const [ex, ey] = project(headX + o.side * 0.45, z, headH);
  const armW = n(Math.max((FOCAL * 0.11) / z, 0.6));

  // 등갓: 도로와 나란한 납작한 판(길이 1.1m, 두께 0.2m) + 아래쪽 밝은 발광면
  const head = box(headX, 1.1, z, headH - 0.2, headH);
  const lens = box(headX, 0.9, z, headH - 0.24, headH - 0.17);

  // 빛 기둥: 등갓에서 도로까지 아래로 넓게 퍼지는 은은한 사다리꼴
  const cone = pathOf([
    project(headX - 0.45, z, headH - 0.22),
    project(headX + 0.45, z, headH - 0.22),
    project(headX + 2.6, z, 0),
    project(headX - 2.6, z, 0),
  ]);

  return [
    `<ellipse cx="${n(px)}" cy="${n(py)}" rx="${n(pool)}" ry="${n((pool * CAM_H) / z + 1)}" fill="url(#si-pool-warm)" opacity="${fade}"/>`,
    `<path d="${cone}" fill="url(#si-lamp-cone)" opacity="${fade}"/>` +
      `<path d="${pole}" fill="#1a2240"/>` +
      `<path d="M${n(ax)},${n(ay)}Q${n(cx)},${n(cy)} ${n(ex)},${n(ey)}" fill="none" stroke="#1a2240" stroke-width="${armW}" stroke-linecap="round"/>` +
      `<path d="${head}" fill="#26304f"/>` +
      `<path d="${lens}" fill="#fff2d6" opacity="${fade}"/>` +
      `<circle cx="${n(gx)}" cy="${n(gy)}" r="${n((FOCAL * 3.4) / z)}" fill="url(#si-lamp-warm)" opacity="${fade}"/>`,
  ];
}

// 다리 위 가로등: 양쪽이 같은 자리에서 마주 보도록 일정한 간격으로
function makeLamps() {
  const lamps = [];
  for (let z = 30; z < TRACK; z += LAMP_PERIOD) {
    for (const side of [-1, 1]) lamps.push({ side, z, x: LAMP_X });
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
