import "./LoadingPreview.css";
import { CARS } from "./cars";

// 로딩 애니메이션 미리보기용 임시 화면 (/loading-preview). 서비스 화면에는 연결되어 있지 않다.
// 세단 → 픽업 → SUV 순서로 선을 그리듯 그려졌다 지워지며 바뀌고, 바퀴 아래로 선 하나가 길어졌다 짧아진다.
// 좌표는 받은 디자인 이미지(세단/픽업/SUV)를 따라 그린 값이고, tx·ty 는 세 차의 바퀴 바닥이 같은 높이(y 160)에 오게 옮기는 값이다.

export default function LoadingPreview() {
  return (
    <main className="lp-page">
      <div className="lp-card" role="status" aria-live="polite">
        <svg className="lp-scene" viewBox="0 0 360 200" aria-hidden="true">
          <path className="lp-road" pathLength="1" d="M300 176 H40" />
          <g className="lp-car">
            {CARS.map((car, i) => (
              <g key={car.name} className="lp-variant" style={{ "--d": `${i * (4 / 3)}s` }} transform={`translate(${car.tx} ${car.ty})`}>
                {car.lines.map((d) => (
                  <path key={d} pathLength="1" d={d} />
                ))}
                {car.wheels.map(([cx, cy]) => (
                  <circle key={cx} className="lp-wheel" pathLength="1" cx={cx} cy={cy} r="23" />
                ))}
              </g>
            ))}
          </g>
        </svg>
        <p className="lp-text">영상을 분석하고 있어요</p>
      </div>
    </main>
  );
}
