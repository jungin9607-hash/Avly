import { CARS } from "../../loading-preview/cars";

// 진행 팝업의 로딩 그림. /loading-preview 미리보기(LoadingPreview)와 같은 그림·움직임이다.
// 차를 네모 프레임(모서리 꺾쇠)에 가두고 세로 스캔선이 프레임 안을 왔다 갔다 한다. 세단 → 픽업 → SUV 가 선을 그리듯 그려졌다가 지워진다(한 바퀴 7.2초).
const W = 680;
const H = 270;
const BOX = { x: 10, y: 10, w: W - 20, h: H - 20 };
const ARM = 30; // 모서리 꺾쇠 길이
const GLOW = 240; // 스캔선 뒤로 남는 빛 띠의 폭
const SLOT = 2.4; // 차 한 대가 그려지고 지워지는 데 쓰는 시간(초)

const right = BOX.x + BOX.w;
const bottom = BOX.y + BOX.h;
const CORNERS = `M${BOX.x} ${BOX.y + ARM} V${BOX.y} H${BOX.x + ARM} M${right - ARM} ${BOX.y} H${right} V${BOX.y + ARM} M${right} ${bottom - ARM} V${bottom} H${right - ARM} M${BOX.x + ARM} ${bottom} H${BOX.x} V${bottom - ARM}`;

export default function CarLoader() {
  return (
    <svg className="md-car" viewBox={`0 0 ${W} ${H}`} aria-hidden="true">
      <defs>
        <linearGradient id="md-car-glow-l" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="currentColor" stopOpacity="0" />
          <stop offset="1" stopColor="currentColor" stopOpacity="0.22" />
        </linearGradient>
        <linearGradient id="md-car-glow-r" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="currentColor" stopOpacity="0.22" />
          <stop offset="1" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
        <clipPath id="md-car-box">
          <rect x={BOX.x} y={BOX.y} width={BOX.w} height={BOX.h} />
        </clipPath>
      </defs>
      <path className="md-car-frame" d={CORNERS} />
      <g clipPath="url(#md-car-box)">
        <g className="md-car-scan" style={{ "--x0": `${BOX.x + 4}px`, "--x1": `${right - 4}px` }}>
          <rect className="md-car-glow md-car-glow-a" x={-GLOW} y={BOX.y} width={GLOW} height={BOX.h} fill="url(#md-car-glow-l)" />
          <rect className="md-car-glow md-car-glow-b" x="2" y={BOX.y} width={GLOW} height={BOX.h} fill="url(#md-car-glow-r)" />
          <path className="md-car-scan-line" d={`M0 ${BOX.y} V${bottom}`} />
        </g>
      </g>
      <g transform={`translate(${(W - 320) / 2 - 20} ${(H - 150) / 2 - 5})`}>
        <g className="md-car-body">
          {CARS.map((car, i) => (
            <g key={car.name} className="md-car-variant" style={{ "--d": `${i * SLOT}s` }} transform={`translate(${car.tx} ${car.ty})`}>
              {car.lines.map((d) => (
                <path key={d} pathLength="1" d={d} />
              ))}
              {car.wheels.map(([cx, cy]) => (
                <circle key={cx} pathLength="1" cx={cx} cy={cy} r="23" />
              ))}
            </g>
          ))}
        </g>
      </g>
    </svg>
  );
}
