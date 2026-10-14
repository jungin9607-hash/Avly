import { VP_X, FOCAL, CAM_H, ROAD_HALF } from "./projection";

/* ---------- 아스팔트 질감 ----------
 * 실제 도로 면에 붙은 질감을 원근 투영해서 그린다. 차선처럼 함께 다가오고,
 * 멀수록 축소본(mip)을 써서 자글거리지 않고 자연스럽게 뭉개진다.
 * 질감 값 d(-1~1): 양수는 밝은 골재 알갱이, 음수는 어두운 틈·얼룩. */
const TEX = 512; // 질감 타일 크기(텍셀)
const TEX_PER_M = 160; // 1m당 텍셀 수 → 타일 하나가 3.2m
const TEX_LEVELS = Math.log2(TEX) + 1;
const ASPHALT_SCALE = 0.75; // 캔버스 해상도 (viewBox 대비)
export const ASPHALT_W = 1440 * ASPHALT_SCALE;
export const ASPHALT_H = 500 * ASPHALT_SCALE;
const ASPHALT_GAIN = 80; // 질감 진하기 (알파 최댓값)
// 큰 얼룩(보수 자국, 기름 얼룩)은 훨씬 넓은 타일로 따로 둬서 반복이 눈에 띄지 않게
const PATCH_PER_M = 10; // 타일 하나가 51.2m
const PATCH_LOD = Math.log2(TEX_PER_M / PATCH_PER_M);

// 이음매 없이 반복되는 부드러운 노이즈를 d에 더함
function addSmooth(d, N, cells, amp) {
  const g = Float32Array.from({ length: cells * cells }, () => Math.random() * 2 - 1);
  const at = (i, j) => g[(j % cells) * cells + (i % cells)];
  const ease = (t) => t * t * (3 - 2 * t);
  for (let y = 0; y < N; y++) {
    const fy = (y / N) * cells;
    const y0 = Math.floor(fy);
    const sy = ease(fy - y0);
    for (let x = 0; x < N; x++) {
      const fx = (x / N) * cells;
      const x0 = Math.floor(fx);
      const sx = ease(fx - x0);
      const top = at(x0, y0) + (at(x0 + 1, y0) - at(x0, y0)) * sx;
      const bot = at(x0, y0 + 1) + (at(x0 + 1, y0 + 1) - at(x0, y0 + 1)) * sx;
      d[y * N + x] += (top + (bot - top) * sy) * amp;
    }
  }
}

// 멀리 볼 때 쓸 축소본: 2×2 평균을 반복
function mipLevels(d) {
  const levels = [d];
  for (let size = TEX / 2; size >= 1; size /= 2) {
    const src = levels[levels.length - 1];
    const dst = new Float32Array(size * size);
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const s = y * 2 * size * 2 + x * 2;
        dst[y * size + x] = (src[s] + src[s + 1] + src[s + size * 2] + src[s + size * 2 + 1]) / 4;
      }
    }
    levels.push(dst);
  }
  return levels;
}

export function makeAsphalt() {
  const N = TEX;
  const rand = (a, b) => a + Math.random() * (b - a);

  // 큰 얼룩 층
  const patch = new Float32Array(N * N);
  addSmooth(patch, N, 8, 0.13);
  addSmooth(patch, N, 32, 0.09);
  addSmooth(patch, N, 128, 0.05);

  // 고운 질감 층: 미세한 굴곡 + 모래 입자
  const d = new Float32Array(N * N);
  addSmooth(d, N, 32, 0.08);
  addSmooth(d, N, 128, 0.08);
  for (let i = 0; i < d.length; i++) d[i] += (Math.random() + Math.random() - 1) * 0.4;

  // 골재 알갱이: 대부분 밝은 돌, 일부는 어두운 구멍
  for (let i = 0; i < N * N * 0.01; i++) {
    const cx = rand(0, N);
    const cy = rand(0, N);
    const r = rand(0.8, 2.4);
    const v = Math.random() < 0.65 ? rand(0.3, 0.8) : rand(-0.9, -0.5);
    for (let y = Math.floor(cy - r); y <= cy + r; y++) {
      for (let x = Math.floor(cx - r); x <= cx + r; x++) {
        const dd = (x - cx) ** 2 + (y - cy) ** 2;
        if (dd > r * r) continue;
        const k = (((y % N) + N) % N) * N + (((x % N) + N) % N);
        d[k] = v * (1 - (0.4 * dd) / (r * r));
      }
    }
  }
  for (let i = 0; i < d.length; i++) d[i] = Math.max(-1, Math.min(1, d[i]));

  return { fine: mipLevels(d), patch: mipLevels(patch) };
}

// 도로 면만 한 줄씩 원근 투영해서 질감을 칠함
export function paintAsphalt(pixels, tex, dist) {
  pixels.fill(0);
  const px = 1 / ASPHALT_SCALE; // 캔버스 1px = viewBox 단위
  const vpx = VP_X / px;
  const wrap = (t) => ((t % TEX) + TEX) % TEX;
  const maxLod = TEX_LEVELS - 1.001;
  for (let row = 0; row < ASPHALT_H; row++) {
    const y = (row + 0.5) * px;
    const z = (FOCAL * CAM_H) / y;
    // 한 픽셀에 들어가는 텍셀 수 → 축소본 단계 (세로가 더 많이 눌림)
    const foot = Math.max((TEX_PER_M * z * px) / FOCAL, (TEX_PER_M * z * z * px) / (FOCAL * CAM_H), 1);
    const lod = Math.min(Math.log2(foot), maxLod);
    const lp = Math.floor(Math.max(0, lod - PATCH_LOD));
    if (lp >= TEX_LEVELS - 2) continue; // 너무 멀면 평균값(≈0)뿐

    // 고운 층: 인접한 두 축소본을 섞어 단계 경계가 보이지 않게
    const l0 = Math.floor(lod);
    const f = lod - l0;
    const a = tex.fine[l0];
    const b = tex.fine[l0 + 1];
    const na = TEX >> l0;
    const nb = na >> 1;
    const v = wrap((z + dist) * TEX_PER_M);
    const rowA = Math.floor(v / (1 << l0)) * na;
    const rowB = Math.floor(v / (1 << (l0 + 1))) * nb;
    // 큰 얼룩 층
    const p = tex.patch[lp];
    const np = TEX >> lp;
    const rowP = Math.floor(wrap((z + dist) * PATCH_PER_M) / (1 << lp)) * np;

    // 가까울수록(전조등 쪽) 질감이 조금 더 잘 보임
    const gain = ASPHALT_GAIN * (0.55 + 0.45 * (y / 500));

    const half = (ROAD_HALF * FOCAL) / z / px;
    const c0 = Math.max(0, Math.floor(vpx - half));
    const c1 = Math.min(ASPHALT_W, Math.ceil(vpx + half));
    const x0 = ((c0 + 0.5) * px - VP_X) * (z / FOCAL); // 이 줄 첫 픽셀의 도로 위 x(m)
    const dx = (px * z) / FOCAL;
    let u = wrap(x0 * TEX_PER_M);
    let up = wrap(x0 * PATCH_PER_M);
    const du = dx * TEX_PER_M;
    const dup = dx * PATCH_PER_M;
    const out = row * ASPHALT_W;
    for (let c = c0; c < c1; c++, u += du, up += dup) {
      if (u >= TEX) u -= TEX;
      if (up >= TEX) up -= TEX;
      const ua = Math.floor(u / (1 << l0));
      const fine = a[rowA + ua] * (1 - f) + b[rowB + (ua >> 1)] * f;
      const val = (fine + p[rowP + Math.floor(up / (1 << lp))]) * gain;
      // 밝은 곳은 흰색, 어두운 곳은 검은색을 반투명으로 얹음 (ABGR)
      pixels[out + c] = val > 0 ? (Math.min(255, val) << 24) | 0xdfe2ea : Math.min(255, -val) << 24;
    }
  }
}
