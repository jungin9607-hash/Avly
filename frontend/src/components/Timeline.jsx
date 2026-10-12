import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import TopNav from "./TopNav";
import LegalNotice from "./LegalNotice";
import "./Timeline.css";

gsap.registerPlugin(ScrollTrigger, useGSAP);

const START = 7.45;
const END = 11.9;

// tone: 결정적 시점(key) · 충돌(impact)은 색으로 구분
const MOMENTS = [
  {
    id: "m5",
    label: "충돌 5초 전",
    time: 7.45,
    summary: "정상 주행 & 거리 확보",
    tag: "정상 주행권 인정",
    title: "본인 정상 주행 및 전방 안전거리 35m 확보",
    hud: "CAM_FRONT",
    badge: "정속 주행 상태",
  },
  {
    id: "m3",
    label: "충돌 3초 전",
    chipLabel: "충돌 3초 전 (가감산 핵심)",
    summaryLabel: "충돌 3초 전 (결정적)",
    time: 9.12,
    summary: "급차선변경 · 깜빡이 미점등",
    tag: "★ 과실 가감산 결정적 요인",
    title: "상대 차량 방향지시등(깜빡이) 미점등 급차선 변경 시작",
    hud: "TELEMETRY_SPEED 46km/h",
    badge: "도로교통법 제38조 위반",
    tone: "key",
  },
  {
    id: "m1",
    label: "충돌 1초 전",
    time: 10.85,
    summary: "충돌 회피 한계 입증",
    tag: "불가항력 회피 한계",
    title: "차간거리 3.4m 급감 및 긴급 제동 (방어운전 노력 입증)",
    hud: "DECEL: -0.62G",
    badge: "방어제동 가동",
  },
  {
    id: "m0",
    label: "충돌 시점",
    time: 11.9,
    summary: "물리적 접촉 좌표 포착",
    tag: "충돌 좌표 확정",
    title: "우측 전면 범퍼-상대 좌측 후미 불가항력 접촉",
    hud: "IMPACT FORCE 1.48G",
    badge: "물리적 충돌 포착",
    tone: "impact",
  },
];

const LAST = MOMENTS.length - 1;
const stamp = (t) => `00:${t.toFixed(2).padStart(5, "0")}`;
const pos = (t) => ((t - START) / (END - START)) * 100;
const two = (n) => String(n).padStart(2, "0");

export default function Timeline() {
  const navigate = useNavigate();
  const root = useRef(null);
  const trackRef = useRef(null);
  const triggerRef = useRef(null); // 가로 이동이 걸린 경우의 ScrollTrigger
  const [active, setActive] = useState(0);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      // 넓은 화면 + 움직임 허용: 세로 스크롤 → 카드가 한 장씩 가로로 넘어감
      // 리듬: [01 보여주기] → 이동 → [02 보여주기] → 이동 → [03] → 이동 → [04 오래 보여주기]
      mm.add("(min-width: 901px) and (prefers-reduced-motion: no-preference)", () => {
        const track = trackRef.current;
        const cards = Array.from(track.children);
        // i번째 카드를 첫 번째 카드 자리(왼쪽)로 가져오는 이동량
        const xFor = (i) => () => -(cards[i].offsetLeft - cards[0].offsetLeft);

        // 시간 단위(아래 숫자들)를 스크롤 길이로 바꾸는 비율: 클수록 전체가 느리고 길어짐
        const UNIT = () => window.innerHeight * 0.75;
        const SHOW = 1; // 한 장면을 멈춰서 보여주는 길이
        const MOVE = 1; // 다음 장면으로 넘어가는 길이
        const LAST_SHOW = 1.6; // 마지막 장면은 더 오래

        const tl = gsap.timeline({ defaults: { ease: "power2.inOut" } });
        const moveStarts = [];
        tl.addLabel("m0", SHOW / 2).to({}, { duration: SHOW });
        for (let i = 1; i <= LAST; i++) {
          moveStarts.push(tl.duration());
          tl.to(track, { x: xFor(i), duration: MOVE });
          const show = i === LAST ? LAST_SHOW : SHOW;
          tl.addLabel(`m${i}`, tl.duration() + show / 2).to({}, { duration: show });
        }

        const st = ScrollTrigger.create({
          animation: tl,
          trigger: ".tl-stage",
          start: "top top",
          end: () => `+=${tl.duration() * UNIT()}`,
          pin: true,
          scrub: 1,
          // 스크롤을 멈추면 가장 가까운 장면에 맞춰 멈춤
          snap: { snapTo: "labels", duration: { min: 0.3, max: 0.8 }, delay: 0.15, ease: "power1.inOut" },
          invalidateOnRefresh: true,
          // 이동이 절반을 넘으면 다음 장면이 '지금'
          onUpdate: (self) => {
            const t = self.progress * tl.duration();
            setActive(moveStarts.filter((s0) => t >= s0 + MOVE / 2).length);
          },
        });
        triggerRef.current = st;
        return () => {
          triggerRef.current = null;
        };
      });
    },
    { scope: root }
  );

  // 좁은 화면 · 움직임 줄이기: 카드 줄을 직접 옆으로 밀면 현재 시점 갱신
  const onTrackScroll = () => {
    if (triggerRef.current) return;
    const track = trackRef.current;
    const max = track.scrollWidth - track.clientWidth;
    setActive(max > 0 ? Math.round((track.scrollLeft / max) * LAST) : 0);
  };

  const goTo = (i) => {
    const idx = Math.max(0, Math.min(LAST, i));
    const st = triggerRef.current;
    if (st) {
      const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.scrollTo({ top: st.labelToScroll(`m${idx}`), behavior: smooth ? "smooth" : "auto" });
    } else {
      const card = trackRef.current.children[idx];
      const pad = parseFloat(getComputedStyle(trackRef.current).paddingLeft) || 0;
      trackRef.current.scrollTo({ left: card.offsetLeft - trackRef.current.offsetLeft - pad, behavior: "smooth" });
    }
  };

  const m = MOMENTS[active];

  return (
    <div className="tl" ref={root}>
      <TopNav active="타임라인" theme="dark" />

      <section className="tl-stage">
        {/* 왼쪽: 제목 · 비율 · 지금 보고 있는 시점 */}
        <div className="tl-side">
          {/* 뒤에 깔리는 큰 단계 숫자: 장면이 바뀌면 함께 바뀜 */}
          <span className={`tl-bignum tl-mono ${m.tone || ""}`} key={`n-${m.id}`} aria-hidden="true">
            {two(active + 1)}
          </span>

          <p className="tl-kicker">
            <IconBranch />
            4단계 핵심 판단 타임라인 요약
          </p>
          <h1>
            사고 순간
            <br />
            <span className="tl-h1-accent">타임라인</span>
          </h1>
          <div className={`tl-now ${m.tone || ""}`} key={m.id} aria-live="polite">
            <p className="tl-now-step">
              STEP {two(active + 1)} · <span className="tl-mono">{stamp(m.time)}</span>
            </p>
            <p className="tl-now-label">{m.summaryLabel || m.label}</p>
            <p className="tl-now-text">{m.summary}</p>
            <ol className="tl-now-dots" aria-hidden="true">
              {MOMENTS.map((mo, i) => (
                <li key={mo.id} className={i <= active ? "on" : ""} />
              ))}
            </ol>
          </div>

          <div className="tl-counter">
            <span className="tl-mono">
              <b>{two(active + 1)}</b> — {two(MOMENTS.length)}
            </span>
            <button type="button" aria-label="이전 시점" onClick={() => goTo(active - 1)} disabled={active === 0}>
              ←
            </button>
            <button type="button" aria-label="다음 시점" onClick={() => goTo(active + 1)} disabled={active === LAST}>
              →
            </button>
          </div>

          <button type="button" className="tl-link" onClick={() => navigate("/analysis-test")}>
            <IconChart />
            과실 산정 근거 요약
          </button>
        </div>

        {/* 오른쪽: 시점 바로가기 · 가로로 흐르는 카드 · 시간축 */}
        <div className="tl-right">
          <div className="tl-right-head">
            <p className="tl-right-label">
              <i aria-hidden="true" />
              BLACKBOX TIMELINE
            </p>
            {/* 지금 보고 있는 장면의 시각: 장면이 바뀌면 같이 바뀜 */}
            <p className={`tl-timecode tl-mono ${m.tone || ""}`} key={m.id}>
              {stamp(m.time)}
            </p>
          </div>
          <div className="tl-chips" role="tablist" aria-label="핵심 시점">
            <button type="button" role="tab" aria-selected={false} className="tl-chip" onClick={() => goTo(0)}>
              전체 핵심 시점 <span className="tl-count">{MOMENTS.length}</span>
            </button>
            {MOMENTS.map((mo, i) => (
              <button
                key={mo.id}
                type="button"
                role="tab"
                aria-selected={active === i}
                className={`tl-chip ${mo.tone || ""} ${active === i ? "is-on" : ""}`}
                onClick={() => goTo(i)}
              >
                <i aria-hidden="true" />
                {mo.chipLabel || mo.label}
              </button>
            ))}
          </div>

          <div className="tl-viewport">
            <ol className="tl-track" ref={trackRef} onScroll={onTrackScroll}>
              {MOMENTS.map((mo, i) => (
                <li key={mo.id} className={`tl-card ${mo.tone || ""} ${active === i ? "is-active" : ""}`}>
                  <figure className="tl-frame">
                    <Scene id={mo.id} />
                    <span className="tl-rec">REC</span>
                    <figcaption className="tl-hud tl-mono">
                      T: {stamp(mo.time)} · {mo.hud}
                    </figcaption>
                    <span className="tl-badge">{mo.badge}</span>
                  </figure>
                  <div className="tl-card-body">
                    <p className="tl-when">
                      {mo.label} <span className="tl-mono">[{stamp(mo.time)}]</span>
                      <span className="tl-tag">{mo.tag}</span>
                    </p>
                    <h2>{mo.title}</h2>
                    {/* TODO: 해당 시점 영상 재생과 연결 */}
                    <button type="button" className="tl-play">
                      <IconPlay />
                      영상보기
                    </button>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          {/* 실제 시각 비율대로 놓인 시간축: 지나온 구간이 채워짐 */}
          <div className="tl-axis">
            <span className="tl-axis-line" />
            <span className="tl-axis-fill" style={{ width: `${pos(m.time)}%` }} />
            {MOMENTS.map((mo, i) => (
              <button
                key={mo.id}
                type="button"
                aria-label={`${mo.label} ${stamp(mo.time)}`}
                className={`tl-axis-dot ${mo.tone || ""} ${i <= active ? "is-past" : ""} ${i === 0 ? "is-first" : ""} ${
                  i === LAST ? "is-last" : ""
                }`}
                style={{ left: `${pos(mo.time)}%` }}
                onClick={() => goTo(i)}
              >
                <em className="tl-mono">{stamp(mo.time)}</em>
              </button>
            ))}
          </div>
        </div>
      </section>

      <div className="tl-bottom">
        <LegalNotice tone="dark" />
      </div>
    </div>
  );
}

/* ---------- 장면 그림 (블랙박스 화면 자리) ---------- */

// 뒤에서 본 승용차. brake: 제동등 켜짐
function Car({ x, y, s, rotate = 0, brake = false }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${rotate}) scale(${s})`}>
      <path d="M-28 -16 Q-25 -27 -14 -28 H14 Q25 -27 28 -16 Z" fill="#3a3d48" />
      <path d="M-22 -17 Q-19 -24 -12 -25 H12 Q19 -24 22 -17 Z" fill="#16171d" />
      <rect x="-36" y="-17" width="72" height="24" rx="4" fill="#5b5f6c" />
      <rect x="-33" y="-12" width="13" height="6" rx="1.5" fill={brake ? "#ff4d4d" : "#6b2a2a"} />
      <rect x="20" y="-12" width="13" height="6" rx="1.5" fill={brake ? "#ff4d4d" : "#6b2a2a"} />
      {brake && (
        <>
          <circle cx="-26" cy="-9" r="9" fill="#ff4d4d" opacity="0.25" />
          <circle cx="26" cy="-9" r="9" fill="#ff4d4d" opacity="0.25" />
        </>
      )}
      <rect x="-10" y="-3" width="20" height="6" rx="1" fill="#d9d9de" />
      <rect x="-32" y="7" width="10" height="6" rx="2" fill="#111" />
      <rect x="22" y="7" width="10" height="6" rx="2" fill="#111" />
    </g>
  );
}

function Scene({ id }) {
  return (
    <svg className="tl-scene" viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <linearGradient id={`sky-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#15161f" />
          <stop offset="1" stopColor="#2c2d3d" />
        </linearGradient>
      </defs>
      <rect width="320" height="72" fill={`url(#sky-${id})`} />
      <rect y="70" width="320" height="110" fill="#22232b" />
      <polygon points="146,70 174,70 330,180 -10,180" fill="#2d2e37" />
      <path d="M151 70 L40 180 M169 70 L280 180" stroke="#b8b8c4" strokeWidth="1.5" opacity="0.55" />
      <path d="M160 70 L160 180" stroke="#e2b25a" strokeWidth="1.5" opacity="0.7" />
      <path d="M155 70 L100 180 M165 70 L220 180" stroke="#fff" strokeWidth="1.2" strokeDasharray="7 9" opacity="0.35" />

      {id === "m5" && (
        <>
          <Car x={138} y={98} s={0.42} />
          <path d="M132 176 L136 106" stroke="#f6cdf9" strokeWidth="1.2" strokeDasharray="3 4" />
          <text x="142" y="146" fill="#f6cdf9" fontSize="10" fontWeight="700">
            35m
          </text>
        </>
      )}
      {id === "m3" && (
        <>
          <defs>
            <marker id={`arrow-${id}`} viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0 0 L10 5 L0 10 z" fill="#f6cdf9" />
            </marker>
          </defs>
          <Car x={212} y={112} s={0.68} rotate={-14} />
          <rect x="184" y="88" width="58" height="38" fill="none" stroke="#f6cdf9" strokeWidth="1.3" strokeDasharray="4 3" />
          <path className="tl-arrow" d="M196 128 Q170 140 150 150" stroke="#f6cdf9" strokeWidth="2" fill="none" markerEnd={`url(#arrow-${id})`} />
          <text x="186" y="82" fill="#f6cdf9" fontSize="9" fontWeight="700">
            깜빡이 OFF
          </text>
        </>
      )}
      {id === "m1" && (
        <>
          <Car x={150} y={132} s={1.15} brake />
          <path d="M150 178 L150 150" stroke="#f6cdf9" strokeWidth="1.2" strokeDasharray="3 3" />
          <text x="156" y="172" fill="#f6cdf9" fontSize="10" fontWeight="700">
            3.4m
          </text>
        </>
      )}
      {id === "m0" && (
        <>
          <Car x={176} y={146} s={1.6} rotate={-6} brake />
          <circle className="tl-ring" cx="122" cy="160" r="10" fill="none" stroke="#ff8a7a" strokeWidth="2" />
          <path
            d="M122 146 L126 155 L136 152 L129 160 L137 168 L126 165 L122 175 L118 165 L107 168 L115 160 L108 152 L118 155 Z"
            fill="#ff8a7a"
          />
        </>
      )}
    </svg>
  );
}

/* ---------- 아이콘 ---------- */
const Svg = ({ children, size = 16 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.9"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);
const IconBranch = () => (
  <Svg>
    <path d="M12 21v-7M12 14 6 4M12 14l6-10" />
  </Svg>
);
const IconChart = () => (
  <Svg>
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <path d="M8 16v-4M12 16V8M16 16v-6" />
  </Svg>
);
const IconPlay = () => (
  <Svg>
    <circle cx="12" cy="12" r="9" />
    <path d="m10 8.5 5 3.5-5 3.5z" fill="currentColor" />
  </Svg>
);
