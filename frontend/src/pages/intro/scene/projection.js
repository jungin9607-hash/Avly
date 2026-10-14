/* ---------- 도로 원근 투영 ----------
 * 실제 도로 치수(m)를 화면 좌표로 투영한다.
 * 카메라 높이 CAM_H, 화면 아래 끝(y=500)이 Z_NEAR 거리, 지평선이 y=0.
 * 멀어질수록 차선 폭·점선 길이·간격이 함께 줄어들어 원근감이 생긴다. */
export const VP_X = 720;
export const CAM_H = 4.0; // 조금 높여서 다리 너머 바다가 더 보이게
export const Z_NEAR = 6;
export const FOCAL = (500 * Z_NEAR) / CAM_H;
export const Z_START = 4; // 화면 아래 바깥에서부터 그림
export const Z_FAR = 800;

export const ROAD_HALF = 7.6; // 갓길 포함 도로 반폭
export const EDGE_X = 6.9; // 바깥 흰 실선
export const CENTER_X = 0.13; // 노란 중앙 이중선
export const LANE_X = [-3.5, 3.5]; // 흰 점선
export const LINE_W = 0.12;

export const DASH_LEN = 3; // 점선 길이 3m, 간격 5m
export const DASH_PERIOD = 8;
export const DASH_MAX_Z = 260;
export const TRACK = 800; // 길가 풍경이 반복되는 거리(m). DASH_PERIOD의 배수
export const SPEED = 20; // m/s

export const project = (x, z, h = 0) => [VP_X + (FOCAL * x) / z, (FOCAL * (CAM_H - h)) / z];
export const pathOf = (pts) => "M" + pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join("L") + "Z";
export const strip = (x, w, z1, z2) =>
  pathOf([project(x - w / 2, z1), project(x + w / 2, z1), project(x + w / 2, z2), project(x - w / 2, z2)]);

// 좌표를 소수 첫째 자리 문자열로 (SVG 문자열을 짧게)
export const n = (v) => v.toFixed(1);
// 거리 z에 서 있는 폭 w, 높이 h1~h2의 세로 사각형 (기둥, 등)
export const box = (x, w, z, h1, h2) => {
  const [x1, y1] = project(x - w / 2, z, h1);
  const [x2, y2] = project(x + w / 2, z, h2);
  return pathOf([[x1, y1], [Math.max(x2, x1 + 0.6), y1], [Math.max(x2, x1 + 0.6), y2], [x1, y2]]);
};
