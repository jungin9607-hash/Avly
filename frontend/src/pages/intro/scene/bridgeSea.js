import { VP_X, CAM_H, FOCAL, Z_START, Z_FAR, ROAD_HALF, project, pathOf, strip, n } from "./projection";

/* ---------- 다리 · 밤바다 ----------
 * 도로는 바다 위 다리. 도로 바깥에 보도(다리 상판)와 바깥 난간이 있고,
 * 그 아래 SEA_DEPTH(m)에 바다가 있다. 바다는 같은 원근으로 투영해서 다리와 함께 지나간다.
 * 문구와 경쟁하지 않도록 어둡고 은은하게: 옅은 잔물결 선만, 픽셀 계산 없이 그린다. */
export const DECK_EDGE = 9.3; // 다리 상판 바깥 끝 (좁을수록 바다가 더 보임)
export const BRIDGE_RAIL_X = [-9.15, 9.15];
export const BRIDGE_RAIL_H = 1.1;
export const BRIDGE_POST_PERIOD = 2.5; // TRACK의 약수
export const BRIDGE_POST_MAX_Z = 400; // 지평선 쪽까지 기둥이 줄지어 보이게
export const FAR_BRIDGE_Z = 70; // 이보다 먼 다리는 안개에 묻히지 않게 안개 위에 한 번 더 밝게 그림
const sideStrip = (x1, x2) => [-1, 1].map((s) => strip((s * (x1 + x2)) / 2, x2 - x1, Z_START, Z_FAR)).join("");
export const DECK = sideStrip(ROAD_HALF, DECK_EDGE);
export const DECK_LIP = sideStrip(DECK_EDGE - 0.08, DECK_EDGE); // 바다와 맞닿는 상판 모서리
const bridgeRail = (h1, h2) =>
  BRIDGE_RAIL_X.map((x) => pathOf([project(x, Z_START, h1), project(x, Z_START, h2), project(x, Z_FAR, h2), project(x, Z_FAR, h1)])).join("");
export const BRIDGE_RAILS = bridgeRail(BRIDGE_RAIL_H - 0.06, BRIDGE_RAIL_H) + bridgeRail(0.52, 0.56);
const farBridgeRail = (h1, h2) =>
  BRIDGE_RAIL_X.map((x) =>
    pathOf([project(x, FAR_BRIDGE_Z, h1), project(x, FAR_BRIDGE_Z, h2), project(x, Z_FAR, h2), project(x, Z_FAR, h1)])
  ).join("");
export const FAR_BRIDGE_RAILS = farBridgeRail(BRIDGE_RAIL_H - 0.08, BRIDGE_RAIL_H) + farBridgeRail(0.5, 0.56);
// 먼 쪽 다리 상판 가장자리(바다와 맞닿는 선)
export const FAR_DECK_LIP = [-1, 1].map((s) => strip(s * (DECK_EDGE - 0.15), 0.3, FAR_BRIDGE_Z, Z_FAR)).join("");

const SEA_DEPTH = 18;
const SEA_H = CAM_H + SEA_DEPTH; // 카메라에서 바다 면까지 높이
const WAVE_LOOP = 900; // 잔물결이 반복되는 구간(m)
const WAVE_MIN_Z = (FOCAL * SEA_H) / 500; // 이보다 가까운 바다는 화면 아래 밖
const WAVE_MAX_Z = 700; // 이보다 먼 물결은 지평선 안개에 묻힘
const SEA_HIDDEN_X = (DECK_EDGE * SEA_H) / CAM_H; // 이보다 다리에 가까운 바다는 상판에 가려 안 보임
const LAMP_SEA_H = 50; // 가로등 빛이 바다에 퍼지는 정도(클수록 넓게)

// 잔물결: 바다 위 고정된 위치의 짧은 가로 선. 다리 상판에 가리지 않는 바깥쪽에만 둠
function makeWaves() {
  const rand = (a, b) => a + Math.random() * (b - a);
  return Array.from({ length: 360 }, (_, i) => ({
    x: (i % 2 ? 1 : -1) * rand(SEA_HIDDEN_X, 650),
    z: rand(0, WAVE_LOOP),
    len: rand(2.5, 9),
  }));
}
const WAVES = makeWaves();

// 평소 물결은 두 묶음으로 나눠 CSS로 번갈아 은은하게 반짝이게 하고,
// 가로등 근처 물결은 따뜻한 빛을 받은 묶음(가까울수록 밝게)으로 따로 모음
// litLamps: 이번 프레임 가로등들 [{ x, z, fade }]
export function drawWaves(dist, litLamps) {
  const groups = ["", "", "", ""]; // 평소 A, 평소 B, 빛 받음(약), 빛 받음(강)
  WAVES.forEach((w, i) => {
    const z = WAVE_MIN_Z + ((((w.z - dist) % WAVE_LOOP) + WAVE_LOOP) % WAVE_LOOP);
    if (z > WAVE_MAX_Z) return;
    const cx = VP_X + (FOCAL * w.x) / z;
    const half = (FOCAL * w.len) / z / 2;
    if (cx + half < 0 || cx - half > 1440) return;
    const y = (FOCAL * SEA_H) / z;
    const th = Math.min(2.4, Math.max(0.6, (FOCAL * SEA_H * 0.8) / (z * z)));
    let lit = 0;
    for (const l of litLamps) {
      const d2 = (w.x - l.x) ** 2 + (z - l.z) ** 2;
      lit = Math.max(lit, l.fade * ((LAMP_SEA_H * LAMP_SEA_H) / (d2 + LAMP_SEA_H * LAMP_SEA_H)) ** 1.5);
    }
    const g = lit > 0.3 ? 3 : lit > 0.12 ? 2 : i % 4 < 2 ? 0 : 1;
    groups[g] += pathOf([[cx - half, y], [cx + half, y], [cx + half, y + th], [cx - half, y + th]]);
  });
  return groups;
}

// 가로등이 바다를 넓게 비춘 빛: 다리 바깥쪽 바다 면에 큰 타원.
// 다리 바로 아래 바다는 상판에 가려 안 보이므로, 빛의 중심을 보이는 바다 쪽(SEA_HIDDEN_X 바깥)에 둠
export function drawSeaGlows(litLamps) {
  return litLamps
    .filter((l) => l.z > 40) // 더 가까우면 빛의 중심이 화면 밖이고 타원만 지나치게 커짐
    .map((l) => {
      const R = 55;
      const cx = VP_X + (FOCAL * Math.sign(l.x) * (SEA_HIDDEN_X + 12)) / l.z;
      const cy = (FOCAL * SEA_H) / l.z;
      const rx = (FOCAL * R) / l.z;
      const ry = Math.min(rx, (FOCAL * SEA_H * R) / (l.z * l.z));
      return `<ellipse cx="${n(cx)}" cy="${n(cy)}" rx="${n(rx)}" ry="${n(ry)}" fill="url(#si-sea-glow)" opacity="${n(l.fade)}"/>`;
    })
    .join("");
}

// 먼 해안 도시 불빛: 지평선 양옆에만(가운데 문구 쪽은 비움), 바다에 짧게 비침
// + 그 앞을 화면 끝에서 끝까지 가로지르는 먼 바다 위 다리(farBridge)
export function makeSkyline() {
  const rand = (a, b) => a + Math.random() * (b - a);
  const warm = ["#ffd9a0", "#ffc27a", "#f2e6d0", "#dfe6ff"];
  const lights = [];
  const reflections = [];
  const glows = [];
  const beacons = [];
  const clusters = [
    [rand(70, 160), rand(90, 170)],
    [rand(250, 380), rand(120, 200)],
    [rand(470, 540), rand(50, 90)],
    [rand(900, 970), rand(50, 90)],
    [rand(1060, 1190), rand(120, 200)],
    [rand(1280, 1370), rand(90, 170)],
  ];
  for (const [c, w] of clusters) {
    glows.push({ x: c, rx: w / 2 });
    const count = Math.round(w / 4);
    for (let i = 0; i < count; i++) {
      const dx = rand(-w / 2, w / 2);
      const tall = 1 - Math.abs(dx / (w / 2)) ** 1.5; // 가운데가 높은 스카이라인
      const y = 30 - rand(0.6, 1.5 + tall * 13);
      const color = warm[Math.floor(Math.random() * warm.length)];
      const o = rand(0.55, 1);
      lights.push({ x: c + dx, y, r: rand(0.55, 1), color, o });
      if (Math.random() < 0.4) reflections.push({ x: c + dx, len: rand(3, 10), color, o: o * 0.6 });
    }
    beacons.push({ x: c + rand(-w / 8, w / 8), y: 30 - (14 + rand(0.5, 2)), delay: rand(0, 2.4) });
  }

  // 지평선을 가로지르는 먼 바다 위 다리: 화면 끝에서 끝까지 끊김 없이 이어짐
  //   상판(가는 선) + 일정한 간격의 가로등 불빛 줄 + 교각 + 양쪽 주탑과 부채꼴 케이블(사장교)
  const DECK_Y = 28.4; // 지평선(30) 바로 위
  const deckLamps = [];
  for (let x = 4; x < 1440; x += 9) {
    const color = Math.random() < 0.85 ? "#ffd59a" : "#f2e6d0";
    deckLamps.push({ x: x + rand(-0.6, 0.6), color, o: rand(0.6, 0.95) });
    if (Math.random() < 0.3) reflections.push({ x, len: rand(2, 6), color, o: 0.35 });
  }
  const piers = [];
  for (let x = 14; x < 1440; x += 28) piers.push(x); // 교각 간격을 좁혀 다리를 든든히 받치는 느낌
  const pylons = [rand(250, 330), rand(1110, 1190)].map((x) => {
    const top = DECK_Y - rand(11, 13);
    const cables = [];
    for (let i = 1; i <= 6; i++) {
      for (const d of [-1, 1]) cables.push({ x2: x + d * i * 11, y1: top + i * 0.9 });
    }
    beacons.push({ x, y: top - 0.6, delay: rand(0, 2.4) });
    return { x, top, cables };
  });
  const farBridge = { deckY: DECK_Y, deckLamps, piers, pylons };

  return { lights, reflections, glows, beacons, farBridge };
}
