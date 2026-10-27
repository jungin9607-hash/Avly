import { SPEED, FOCAL, CAM_H, project, pathOf, strip, n, box } from "./projection";

/* ---------- 다른 차들 ----------
 * 오른쪽 두 차로는 같은 방향. 반드시 우리보다 빨라서(v > SPEED) 화면 아래 어둠 속에서
 *   나타나 앞질러 가다가 지평선 안개 속으로 사라진다(빨간 미등).
 * 왼쪽 두 차로는 마주 오는 차. 지평선에서 나타나 전조등을 켜고 다가와
 *   화면 아래의 어둠(.si-road-shade) 속으로 지나간다.
 * 속도(v, m/s)는 우리 차(SPEED = 시속 72km) 기준으로 무리 없어 보이게 잡았다.
 * 같은 차로의 차들은 속도가 같아서 서로 겹치지 않고,
 * 사라졌다 다시 나타날 때마다 차종과 색이 바뀐다. */
const CAR_LOOP = 360; // 차들이 반복되는 구간 길이(m)
const CAR_MIN_Z = 3; // 이보다 가까우면 화면 아래로 지나간 것
const CAR_FADE = [200, 340]; // 이 거리 사이에서 안개 속으로 사라짐
const CAR_LANES = [
  // 1차선(중앙선 옆)은 상대 속도를 낮춰 화면에 더 오래 머물게
  { x: 1.75, dir: 1, v: 25, count: 3 }, // 시속 90km (우리보다 18km 빠름)
  { x: 5.2, dir: 1, v: 27, count: 3 }, // 시속 약 97km (우리보다 25km 빠름)
  { x: -1.75, dir: -1, v: 6, count: 3 }, // 시속 약 22km (상대 94km)
  { x: -5.2, dir: -1, v: 10, count: 2 }, // 시속 36km (상대 108km)
];
// 밤이라 채도를 뺀 차체 색: [앞·뒷면, 옆면, 지붕·보닛]
const CAR_COLORS = [
  ["#1d2233", "#141826", "#2e3550"],
  ["#26272e", "#1a1b21", "#3b3d48"],
  ["#4b4e5c", "#363945", "#6d7184"],
  ["#3a1f2a", "#2a1520", "#553245"],
  ["#7c7f8c", "#5b5e6b", "#9da0ae"],
  ["#1f3530", "#162621", "#2f4d46"],
];
// 스포츠카는 밤에도 눈에 띄는 진한 색
const SPORT_COLORS = [
  ["#5a1a1e", "#3e1215", "#7a2a2e"],
  ["#1e3566", "#152548", "#2c4a8a"],
  ["#6b5a22", "#4d4018", "#8c7630"],
  ["#17181d", "#0f1013", "#2a2c34"],
];
const GLASS = "#0b0d16";
const GLASS_TOP = "#1a1f33"; // 앞·뒤 유리는 하늘을 비춰 조금 밝게

/* 차종: 앞 끝에서부터 잰 옆모습 윤곽 [거리(m), 높이(m)].
 * glass: 유리인 윤곽 구간 번호, bed: 안이 비어 어두운 구간(짐칸),
 * cabin: 옆 유리창 범위,
 * rearGlass: 뒷면 자체에 있는 유리(승합차) 높이 */
const CAR_TYPES = [
  {
    name: "sedan", weight: 3, W: 0.9, H0: 0.3, belt: 0.92, r: 0.33, wheels: [0.9, 3.65], cabin: [1.0, 4.1],
    profile: [[0, 0.74], [0.95, 0.86], [1.9, 1.42], [3.5, 1.42], [4.2, 1.0], [4.7, 0.96]],
    glass: [1, 3], head: [0.6, 0.7], tail: [0.74, 0.86],
  },
  {
    name: "suv", weight: 2.5, W: 0.95, H0: 0.38, belt: 1.08, r: 0.38, wheels: [0.9, 3.75], cabin: [1.0, 4.35],
    profile: [[0, 0.95], [0.9, 1.06], [1.75, 1.7], [4.3, 1.68], [4.45, 1.6], [4.6, 1.05]],
    glass: [1, 4], head: [0.78, 0.9], tail: [0.95, 1.1],
  },
  {
    name: "compact", weight: 1.6, W: 0.8, H0: 0.28, belt: 0.9, r: 0.3, wheels: [0.65, 2.95], cabin: [0.75, 3.3],
    profile: [[0, 0.72], [0.6, 0.82], [1.5, 1.48], [3.3, 1.46], [3.6, 0.92]],
    glass: [1, 3], head: [0.6, 0.7], tail: [0.72, 0.85],
  },
  {
    name: "van", weight: 1.2, W: 0.98, H0: 0.35, belt: 1.1, r: 0.36, wheels: [0.95, 4.15], cabin: [1.45, 5.0],
    profile: [[0, 0.92], [0.55, 1.08], [1.45, 1.95], [5.05, 1.95], [5.2, 1.88]],
    glass: [1], rearGlass: [1.2, 1.75], head: [0.8, 0.92], tail: [0.95, 1.35], pillars: 1.2,
  },
  {
    name: "pickup", weight: 1, W: 0.88, H0: 0.4, belt: 1.18, r: 0.34, wheels: [1.0, 3.9], cabin: [0.2, 1.6],
    profile: [[0, 1.0], [0.18, 1.92], [1.68, 1.95], [1.72, 1.08], [5.1, 1.08]],
    glass: [0], bed: [3], head: [0.7, 0.82], tail: [0.62, 0.8],
  },
  {
    // 낮고 넓은 차체, 긴 보닛, 뒤로 흘러내리는 유리 지붕, 끝에 작은 스포일러
    name: "sports", weight: 0.8, W: 0.96, H0: 0.18, belt: 0.8, r: 0.33, wheels: [1.05, 3.6], cabin: [1.6, 3.9],
    profile: [[0, 0.6], [1.45, 0.8], [2.15, 1.18], [2.9, 1.2], [4.0, 0.9], [4.4, 0.86], [4.5, 0.92]],
    glass: [1, 3], head: [0.52, 0.6], tail: [0.7, 0.79], colors: SPORT_COLORS,
  },
];

// 진행 방향에 맞춰 윤곽을 뒤집어 둠: 뒷면이 보이는 차는 뒤 끝이 0
function orient(t, rear) {
  const L = t.profile[t.profile.length - 1][0];
  const nSeg = t.profile.length - 1;
  if (!rear) return { ...t, L, rear, glass: t.glass || [], light: t.head };
  const flip = (zo) => L - zo;
  return {
    ...t,
    L,
    rear,
    profile: t.profile.map(([zo, h]) => [flip(zo), h]).reverse(),
    glass: (t.glass || []).map((i) => nSeg - 1 - i),
    bed: (t.bed || []).map((i) => nSeg - 1 - i),
    cabin: [flip(t.cabin[1]), flip(t.cabin[0])],
    wheels: t.wheels.map(flip),
    faceGlass: t.rearGlass,
    light: t.tail,
  };
}
const CAR_SHAPES = CAR_TYPES.map((t) => ({ front: orient(t, false), rear: orient(t, true) }));

// 같은 입력이면 항상 같은 0~1 값 (차가 다시 나타날 때마다 차종을 고르는 데 사용)
function hash01(a) {
  let h = Math.imul(a ^ 0x9e3779b9, 0x85ebca6b);
  h ^= h >>> 13;
  h = Math.imul(h, 0xc2b2ae35);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}
// weight 비율대로 차종을 고름
const CAR_WEIGHT_SUM = CAR_TYPES.reduce((a, t) => a + t.weight, 0);
function pickType(r) {
  let acc = 0;
  for (let i = 0; i < CAR_TYPES.length; i++) {
    acc += CAR_TYPES[i].weight / CAR_WEIGHT_SUM;
    if (r < acc) return i;
  }
  return CAR_TYPES.length - 1;
}

function makeCars() {
  const rand = (a, b) => a + Math.random() * (b - a);
  const cars = [];
  const seed = Math.floor(Math.random() * 1e6);
  for (const lane of CAR_LANES) {
    const gap = CAR_LOOP / lane.count;
    for (let i = 0; i < lane.count; i++) {
      cars.push({
        id: seed + cars.length * 7919,
        x: lane.x,
        dir: lane.dir,
        // 이동 거리 1m당 우리 쪽으로 다가오는 거리 (음수면 멀어짐)
        k: 1 - (lane.dir * lane.v) / SPEED,
        z: i * gap + rand(0, gap * 0.5),
      });
    }
  }
  return cars;
}
const CARS = makeCars();

// 차 한 대: 바닥 그림자 → 옆면(창·바퀴) → 윗면들(먼 쪽부터) → 앞(뒤)면 → 불빛
function drawCar(m, color, o, z) {
  const cx = o.x;
  const s = Math.sign(cx); // 카메라 쪽(안쪽) 옆면이 보임
  const xi = cx - s * m.W;
  const { W, H0, L, profile } = m;
  const [face, side, top] = color;
  const P = (x, zo, h) => project(x, z + zo, h);
  const poly = (pts, fill) => `<path d="${pathOf(pts)}" fill="${fill}"/>`;
  const heightAt = (zo) => {
    for (let i = 0; i < profile.length - 1; i++) {
      const [za, ha] = profile[i];
      const [zb, hb] = profile[i + 1];
      if (zo >= za && zo <= zb) return zb === za ? Math.max(ha, hb) : ha + ((hb - ha) * (zo - za)) / (zb - za);
    }
    return profile[profile.length - 1][1];
  };

  let out = "";
  if (!m.rear) {
    // 마주 오는 차의 전조등이 앞 도로를 비춤
    const zb = Math.max(z - 7, z * 0.55);
    const [bx, by] = project(cx, zb, 0);
    const rx = (FOCAL * (1.8 + W - 0.9)) / zb;
    out += `<ellipse cx="${n(bx)}" cy="${n(by)}" rx="${n(rx)}" ry="${n((rx * CAM_H) / zb + 1)}" fill="url(#si-car-beam)"/>`;
  }
  out += `<path d="${strip(cx, W * 2 + 0.3, z - 0.2, z + L + 0.2)}" fill="#000" opacity="0.45"/>`;

  // 옆면
  out += poly([P(xi, 0, H0), ...profile.map(([zo, h]) => P(xi, zo, h)), P(xi, L, H0)], side);
  // 옆 유리창: 윤곽에서 조금 내려온 선 ~ 벨트라인
  {
    const [c1, c2] = m.cabin;
    const tops = [c1, ...profile.map(([zo]) => zo).filter((zo) => zo > c1 && zo < c2), c2].map((zo) => [
      zo,
      Math.max(m.belt + 0.08, heightAt(zo) - 0.08),
    ]);
    out += poly([P(xi, c1, m.belt), ...tops.map(([zo, h]) => P(xi, zo, h)), P(xi, c2, m.belt)], GLASS);
    if (m.pillars) {
      let pil = "";
      for (let zo = c1 + m.pillars; zo < c2 - 0.3; zo += m.pillars) {
        pil += pathOf([P(xi, zo - 0.07, m.belt), P(xi, zo - 0.07, heightAt(zo)), P(xi, zo + 0.07, heightAt(zo)), P(xi, zo + 0.07, m.belt)]);
      }
      out += `<path d="${pil}" fill="${side}"/>`;
    }
  }
  // 옆에서 보이는 바퀴
  for (const w of m.wheels) {
    const ring = (rr) =>
      Array.from({ length: 12 }, (_, i) => {
        const t = (i / 12) * Math.PI * 2;
        return P(xi, w + Math.cos(t) * rr, m.r + Math.sin(t) * rr);
      });
    out += poly(ring(m.r), "#07080c") + poly(ring(m.r * 0.45), "#2a2c33");
  }

  // 윗면: 카메라를 향한 면만, 먼 쪽부터
  for (let i = profile.length - 2; i >= 0; i--) {
    const [za, ha] = profile[i];
    const [zb, hb] = profile[i + 1];
    const facing = -(hb - ha) * (-z - za) + (zb - za) * (CAM_H - ha);
    if (facing <= 0) continue;
    const fill = m.glass.includes(i) ? GLASS_TOP : (m.bed || []).includes(i) ? "#0e0f14" : top;
    out += poly([P(cx - W, za, ha), P(cx + W, za, ha), P(cx + W, zb, hb), P(cx - W, zb, hb)], fill);
  }

  // 앞(뒤)면
  const hn = profile[0][1];
  out += poly([P(cx - W, 0, H0), P(cx + W, 0, H0), P(cx + W, 0, hn), P(cx - W, 0, hn)], face);
  if (m.faceGlass) {
    const [g1, g2] = m.faceGlass;
    out += poly([P(cx - W + 0.12, 0, g1), P(cx + W - 0.12, 0, g1), P(cx + W - 0.12, 0, g2), P(cx - W + 0.12, 0, g2)], GLASS_TOP);
  }
  // 범퍼, 번호판, 바퀴 아래쪽
  out += poly([P(cx - W, 0, H0), P(cx + W, 0, H0), P(cx + W, 0, H0 + 0.14), P(cx - W, 0, H0 + 0.14)], "#0d0e13");
  out += `<path d="${box(cx, 0.52, z, H0 + 0.17, H0 + 0.3)}" fill="#c9c6b0" opacity="${m.rear ? 0.55 : 0.3}"/>`;
  out += `<path d="${box(cx - W + 0.22, 0.3, z, 0, H0 + 0.04)}${box(cx + W - 0.22, 0.3, z, 0, H0 + 0.04)}" fill="#07080c"/>`;

  // 미등(빨강) 또는 전조등(흰빛)과 번지는 빛
  const lights = [-1, 1].map((d) => cx + d * (W - 0.22));
  const [lh1, lh2] = m.light;
  const glowR = (FOCAL * (m.rear ? 0.6 : 1.2)) / z;
  out += `<path d="${lights.map((x) => box(x, 0.26, z, lh1, lh2)).join("")}" fill="${m.rear ? "#ff4a4a" : "#fff6dc"}"/>`;
  for (const x of lights) {
    const [gx, gy] = project(x, z, (lh1 + lh2) / 2);
    out += `<circle cx="${n(gx)}" cy="${n(gy)}" r="${n(glowR)}" fill="url(#${m.rear ? "si-tail-glow" : "si-head-glow"})"/>`;
  }

  const fade = Math.min(1, Math.max(0, (CAR_FADE[1] - z) / (CAR_FADE[1] - CAR_FADE[0])));
  return `<g opacity="${n(fade)}">${out}</g>`;
}

// 먼 차부터 그려야 가까운 차가 위에 덮임
export function drawCars(dist) {
  return CARS.map((o) => {
    const raw = o.z - dist * o.k;
    const cycle = Math.floor(raw / CAR_LOOP);
    return [CAR_MIN_Z + (((raw % CAR_LOOP) + CAR_LOOP) % CAR_LOOP), o, cycle];
  })
    .filter(([z]) => z > CAR_MIN_Z + 0.05 && z < CAR_FADE[1])
    .sort((a, b) => b[0] - a[0])
    .map(([z, o, cycle]) => {
      const t = pickType(hash01(o.id + cycle * 104729));
      const palette = CAR_TYPES[t].colors || CAR_COLORS;
      const color = palette[Math.floor(hash01(o.id + cycle * 104729 + 1) * palette.length)];
      return drawCar(CAR_SHAPES[t][o.dir > 0 ? "rear" : "front"], color, o, z);
    })
    .join("");
}
