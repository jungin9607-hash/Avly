import "./LoadingPreview.css";
import { CARS } from "./cars";

// 로딩 애니메이션 미리보기용 임시 화면 (/loading-preview). 서비스 화면에는 연결되어 있지 않다.
// 세단 → 픽업 → SUV 순서로 선을 그리듯 그려졌다가 지워진다. 한 대가 완전히 지워진 뒤에 다음 차가 그려지기 시작한다(한 바퀴 7.2초).
// 차를 네모 프레임(모서리 꺾쇠)에 가두고, 세로 스캔선이 프레임 안을 왔다 갔다 하며 영상을 훑는 느낌을 준다.
// 스캔선 뒤로 남는 빛 띠는 항상 지나온 쪽(움직이는 방향의 반대쪽)에 생긴다.
// 좌표는 받은 디자인 이미지(세단/픽업/SUV)를 따라 그린 값이고, tx·ty 는 세 차의 바퀴 바닥이 같은 높이(y 160)에 오게 옮기는 값이다.
const W = 520; // 그림 전체 폭
const H = 270; // 그림 전체 높이
const BOX = { x: 10, y: 10, w: W - 20, h: H - 20 }; // 네모 프레임
const ARM = 30; // 모서리 꺾쇠 길이
const SLOT = 2.4; // 차 한 대가 그려지고 지워지는 데 쓰는 시간(초). 한 바퀴는 SLOT * 3

const right = BOX.x + BOX.w;
const bottom = BOX.y + BOX.h;
const CORNERS = `M${BOX.x} ${BOX.y + ARM} V${BOX.y} H${BOX.x + ARM} M${right - ARM} ${BOX.y} H${right} V${BOX.y + ARM} M${right} ${bottom - ARM} V${bottom} H${right - ARM} M${BOX.x + ARM} ${bottom} H${BOX.x} V${bottom - ARM}`;

export default function LoadingPreview() {
  return (
    <main className="lp-page">
      <div className="lp-card" role="status" aria-live="polite">
        <svg className="lp-scene" viewBox={`0 0 ${W} ${H}`} aria-hidden="true">
          <defs>
            <linearGradient id="lp-glow-l" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stopColor="currentColor" stopOpacity="0" />
              <stop offset="1" stopColor="currentColor" stopOpacity="0.22" />
            </linearGradient>
            <linearGradient id="lp-glow-r" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stopColor="currentColor" stopOpacity="0.22" />
              <stop offset="1" stopColor="currentColor" stopOpacity="0" />
            </linearGradient>
            <clipPath id="lp-box">
              <rect x={BOX.x} y={BOX.y} width={BOX.w} height={BOX.h} />
            </clipPath>
          </defs>
          <path className="lp-frame" d={CORNERS} />
          <g clipPath="url(#lp-box)">
            <g className="lp-scan" style={{ "--lp-x0": `${BOX.x + 4}px`, "--lp-x1": `${right - 4}px` }}>
              <rect className="lp-glow lp-glow-behind-left" x="-56" y={BOX.y} width="56" height={BOX.h} fill="url(#lp-glow-l)" />
              <rect className="lp-glow lp-glow-behind-right" x="2" y={BOX.y} width="56" height={BOX.h} fill="url(#lp-glow-r)" />
              <path className="lp-scan-line" d={`M0 ${BOX.y} V${bottom}`} />
            </g>
          </g>
          <g transform={`translate(${(W - 320) / 2 - 20} ${(H - 150) / 2 - 5})`}>
            <g className="lp-car">
              {CARS.map((car, i) => (
                <g key={car.name} className="lp-variant" style={{ "--d": `${i * SLOT}s` }} transform={`translate(${car.tx} ${car.ty})`}>
                  {car.lines.map((d) => (
                    <path key={d} pathLength="1" d={d} />
                  ))}
                  {car.wheels.map(([cx, cy]) => (
                    <circle key={cx} className="lp-wheel" pathLength="1" cx={cx} cy={cy} r="23" />
                  ))}
                </g>
              ))}
            </g>
          </g>
        </svg>
        <p className="lp-text">영상을 분석하고 있어요</p>
      </div>
    </main>
  );
}
