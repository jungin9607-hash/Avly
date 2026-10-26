import { useEffect, useState } from "react";
import "./LoadingCrashColor.css";
import yellowUrl from "../../assets/loading-car-yellow.png";
import whiteUrl from "../../assets/loading-car-white.png";
import wheelAUrl from "../../assets/loading-wheel-yellow-a.png";
import wheelBUrl from "../../assets/loading-wheel-yellow-b.png";

// 컬러 차량 로딩 미리보기 화면 (/loading-crash-color). 서비스 화면에는 연결되어 있지 않다.
// 노란 스포츠카가 0~5초 동안 출발·가속해 오른쪽 끝의 흰 세단과 앞범퍼끼리 부딪히고(100%), 반동·흔들림 뒤 페이드아웃한다. 7초 주기로 반복한다.
// 퍼센트는 노란 차가 움직인 거리(출발 위치 → 접촉 위치)를 0~100%로 바꾼 값이며 실제 분석 진행률이 아니다.
const CYCLE = 7;
const DRIVE = 5;
const GROUND = 214; // 바퀴 바닥 y
const TRACK = { x: 40, y: 234, w: 561, h: 12 }; // 세단 출발 위치(왼쪽)부터 SUV 뒤쪽 끝(오른쪽)까지 이어지는 트랙
const S = 0.66; // 차량 그림 크기(그림 좌표 대비)
const SS = S; // 파란 세단 그림 크기
const LOCAL_H = 74; // 차량 그림 안에서 바퀴 바닥 y
const SEDAN_X0 = 40; // 세단 그림의 왼쪽 위치(출발)
const SEDAN_FRONT = 174; // 세단 그림 안에서 앞범퍼의 x
const HIT_X = 479; // 두 앞범퍼가 닿는 x
const SUV_FRONT = 0; // SUV 그림 안에서 앞범퍼의 x
const SUV_X = HIT_X - SUV_FRONT * S; // SUV 그림의 왼쪽 위치(고정)
const START_FRONT = SEDAN_X0 + SEDAN_FRONT * SS; // 출발할 때 세단 앞범퍼 x
const TRACK_END = TRACK.x + TRACK.w;
const DIST = HIT_X - START_FRONT; // 세단이 움직일 수 있는 거리
const SPIKES = [-70, -40, -10, 15, 45];

const clamp01 = (v) => Math.min(Math.max(v, 0), 1);

function pose(t) {
  const u = clamp01(t / DRIVE);
  const moved = DIST * (u * u * 0.55 + u * 0.45); // 천천히 출발해서 점점 빨라진다
  const c = Math.max(t - DRIVE, 0);
  const squash = c < 0.14 ? Math.sin((c / 0.14) * Math.PI) : 0; // 접촉 순간 짧게 눌린다
  const recoil = c > 0.06 ? 1 - Math.exp(-(c - 0.06) * 6) : 0; // 세단이 왼쪽으로 튕겨 나간다
  const lift = c > 0.06 && c < 1 ? Math.sin(((c - 0.06) / 0.94) * Math.PI) : 0; // 세단 앞부분이 들렸다 내려온다
  const push = c > 0.06 ? 1 - Math.exp(-(c - 0.06) * 7) : 0; // SUV가 오른쪽으로 밀린다
  const shake = c > 0.06 ? Math.sin((c - 0.06) * 42) * Math.exp(-(c - 0.06) * 5) : 0; // SUV 차체가 작게 흔들린다
  const fade = t < 0.3 ? t / 0.3 : t > CYCLE - 0.5 ? (CYCLE - t) / 0.5 : 1;
  const sedanDx = moved - 26 * recoil;
  return {
    sedanDx, lift, squash, fade, shake, c,
    suvDx: 14 * push,
    percent: c > 0 ? 100 : Math.min(Math.round(clamp01(moved / DIST) * 100), 99),
    // 바 끝은 세단 앞범퍼를 따라가다가, 부딪힌 직후 SUV 뒤쪽 트랙 끝까지 빠르게 이어서 채워진다
    fillEnd: c > 0 ? HIT_X + (TRACK_END - HIT_X) * (1 - (1 - clamp01(c / 0.35)) ** 3) : START_FRONT + moved,
  };
}

// 붙여 주신 사진(노란 스포츠카, 흰 세단). 그림 안의 좌표는 위 상수들과 같은 단위(폭 175 / 185)로 맞췄다.
// 노란 차는 사진에서 바퀴 안쪽(휠)을 따로 잘라 둔 그림을 차체 위에 얹어 돌린다. 흰 세단 바퀴는 사진 그대로다.
function Yellow({ deg }) {
  return (
    <g>
      <image href={yellowUrl} x="0" y={LOCAL_H - 50.4} width="175" height="49.9" />
      <image href={wheelAUrl} x={28.9 - 12.1} y={LOCAL_H - 15.4 - 12.1} width="24.2" height="24.2" transform={`rotate(${deg} 28.9 ${LOCAL_H - 15.4})`} />
      <image href={wheelBUrl} x={133.9 - 11.7} y={LOCAL_H - 12.6 - 11.7} width="23.4" height="23.4" transform={`rotate(${deg} 133.9 ${LOCAL_H - 12.6})`} />
    </g>
  );
}

// 왼쪽을 보고 서 있는 차(원본 사진이 그대로 왼쪽을 보고 있다)
function White() {
  return <image href={whiteUrl} x="0" y={LOCAL_H - 56.7} width="185" height="56.6" />;
}

export default function LoadingCrashColor() {
  const [reduced] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [t, setT] = useState(reduced ? DRIVE + 0.35 : 0);
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

  const { sedanDx, lift, squash, fade, shake, c, suvDx, percent, fillEnd } = pose(t);
  const sedanX = SEDAN_X0 + sedanDx;
  const sedanDeg = (sedanDx / SS / 11.9) * 57.3; // 바퀴가 구른 거리만큼 돈다
  const axle = [28.9, 58.6]; // 세단 뒷바퀴 축: 앞부분이 들릴 때 이 점을 기준으로 돈다
  const burst = c > 0 && c < 0.45 ? { s: 0.7 + c * 3, o: c < 0.2 ? 1 : 1 - (c - 0.2) / 0.25 } : { s: 0, o: 0 };
  const sedanShadow = { rx: 80 * SS * (1 - 0.06 * lift), o: 0.5 - 0.18 * lift };

  return (
    <main className="lcc-page">
      <div className="lcc-card" role="status" aria-live="polite">
        <svg className="lcc-scene" viewBox="0 100 641 160" aria-hidden="true" style={{ opacity: fade }}>
          <rect className="lcc-track" x={TRACK.x} y={TRACK.y} width={TRACK.w} height={TRACK.h} rx="6" />
          <rect className="lcc-fill" x={TRACK.x} y={TRACK.y} width={Math.max(fillEnd - TRACK.x, TRACK.h)} height={TRACK.h} rx="6" />
          <ellipse cx={sedanX + 87 * SS} cy={GROUND} rx={sedanShadow.rx} ry="4.5" fill="#000" opacity={sedanShadow.o} />
          <ellipse cx={SUV_X + suvDx + 92 * S} cy={GROUND} rx={88 * S} ry="4.5" fill="#000" opacity="0.5" />
          {[28.9, 133.9].map((x) => (
            <ellipse key={`y${x}`} cx={sedanX + x * SS} cy={GROUND} rx={11 * SS} ry="2.4" fill="#000" opacity={0.55 - 0.3 * lift} />
          ))}
          {[22.5, 130.8].map((x) => (
            <ellipse key={`w${x}`} cx={SUV_X + suvDx + x * S} cy={GROUND} rx={13 * S} ry="2.4" fill="#000" opacity="0.55" />
          ))}
          <g transform={`translate(${sedanX} ${GROUND - LOCAL_H * SS}) scale(${SS}) rotate(${-4 * lift} ${axle[0]} ${axle[1]}) translate(${SEDAN_FRONT} 0) scale(${1 - 0.045 * squash} ${1 + 0.02 * squash}) translate(${-SEDAN_FRONT} 0)`}>
            <Yellow deg={sedanDeg} />
          </g>
          <g transform={`translate(${SUV_X + suvDx} ${GROUND - LOCAL_H * S + shake * 1.2}) scale(${S}) rotate(${shake * 1.4} 130.7 61.4) scale(${1 - 0.03 * squash} ${1 + 0.015 * squash})`}>
            <White />
          </g>
          <g transform={`translate(${HIT_X} ${GROUND - 30}) scale(${burst.s * 0.8})`} style={{ opacity: burst.o }} className="lcc-burst">
            {SPIKES.map((deg) => (
              <path key={deg} d="M0 -14 V-46" transform={`rotate(${deg})`} />
            ))}
          </g>
        </svg>
        <p className="lcc-percent">{percent}%</p>
        <p className="lcc-text">영상을 분석하고 있어요</p>
        <p className="lcc-note">퍼센트는 애니메이션 예시이며 실제 분석 진행률이 아니에요</p>
      </div>
    </main>
  );
}
