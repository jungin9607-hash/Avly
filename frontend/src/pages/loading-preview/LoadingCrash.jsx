import { useEffect, useState } from "react";
import "./LoadingCrash.css";
import { CARS } from "./cars";

// 로딩바 미리보기 화면 (/loading-crash). 서비스 화면에는 연결되어 있지 않다.
// 로딩바 위로 세단이 달리고, 100%가 되는 순간 오른쪽 끝에 서 있던 SUV와 부딪힌 뒤 처음부터 다시 반복한다.
const SEDAN = CARS[0];
const SUV = CARS[2];
const CYCLE = 7; // 한 번 반복하는 시간(초)
const DRIVE = 5; // 달리는 시간(초). 이 시간이 지나면 부딪힌다
const S = 0.5; // 자동차 그림 크기
const BAR = { x: 20, y: 180, w: 262 }; // 로딩바. 바퀴가 이 선 위에 닿는다
const HIT_X = BAR.x + BAR.w + 4; // 부딪히는 위치
const START_FRONT = 90; // 세단 앞부분이 처음 있는 위치
const FRONT = { sedan: 340, suv: 350 }; // 자동차 그림에서 앞부분의 x 좌표

const BURST = [0, 60, 120, 180, 240, 300];

function pose(t) {
  const u = Math.min(t / DRIVE, 1);
  const p = u * u * (3 - 2 * u) * 0.35 + u * 0.65; // 천천히 출발해서 점점 빨라진다
  const c = Math.max(t - DRIVE, 0);
  const kick = c < 0.6 ? Math.sin((c / 0.6) * Math.PI) : 0; // 부딪힌 직후 튕겼다가 돌아오는 정도
  const fade = t < 0.3 ? t / 0.3 : t > CYCLE - 0.5 ? (CYCLE - t) / 0.5 : 1;
  return { p, c, kick, fade, bump: t < DRIVE ? Math.sin(t * 34) * 1.6 : 0 };
}

function Car({ car }) {
  return (
    <g transform={`translate(${car.tx} ${car.ty})`}>
      {car.lines.map((d) => (
        <path key={d} d={d} />
      ))}
      {car.wheels.map(([cx, cy]) => (
        <circle key={cx} cx={cx} cy={cy} r="23" />
      ))}
    </g>
  );
}

export default function LoadingCrash() {
  const [reduced] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [t, setT] = useState(reduced ? DRIVE + 0.3 : 0);
  useEffect(() => {
    if (reduced) return undefined;
    let frame;
    const start = performance.now();
    const tick = (now) => {
      setT(((now - start) / 1000) % CYCLE);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [reduced]);

  const { p, c, kick, fade, bump } = pose(t);
  const front = START_FRONT + (HIT_X - START_FRONT) * p;
  const groundY = BAR.y;
  const carY = groundY - 160 * S;
  const moverX = front - FRONT.sedan * S - 16 * kick;
  const suvX = HIT_X + FRONT.suv * S + 10 * kick;
  const fill = Math.min(Math.max(front - BAR.x, 0), BAR.w);
  const percent = Math.round((fill / BAR.w) * 100);
  const burstScale = c > 0 && c < 0.5 ? 0.8 + c * 2.4 : 0;
  const burstOpacity = c > 0 && c < 0.5 ? 1 - c * 2 : 0;

  return (
    <main className="lc-page">
      <div className="lc-card" role="status" aria-live="polite">
        <svg className="lc-scene" viewBox="0 0 460 240" aria-hidden="true" style={{ opacity: fade }}>
          <rect className="lc-track" x={BAR.x} y={groundY} width={BAR.w} height="10" rx="5" />
          <rect className="lc-track" x={HIT_X + 8} y={groundY} width={460 - HIT_X - 28} height="10" rx="5" />
          <rect className="lc-fill" x={BAR.x} y={groundY} width={Math.max(fill, 10)} height="10" rx="5" />
          <g className="lc-car" transform={`translate(${moverX} ${carY + bump}) rotate(${-4 * kick} ${FRONT.sedan * S} ${160 * S}) scale(${S})`}>
            <Car car={SEDAN} />
          </g>
          <g className="lc-car" transform={`translate(${suvX} ${carY}) rotate(${3 * kick} 0 ${160 * S}) scale(${-S} ${S})`}>
            <Car car={SUV} />
          </g>
          <g className="lc-burst" transform={`translate(${HIT_X} ${groundY - 42}) scale(${burstScale})`} style={{ opacity: burstOpacity }}>
            {BURST.map((deg) => (
              <path key={deg} d="M16 0 H34" transform={`rotate(${deg})`} />
            ))}
          </g>
        </svg>
        <p className="lc-percent">{percent}%</p>
        <p className="lc-text">영상을 분석하고 있어요</p>
      </div>
    </main>
  );
}
