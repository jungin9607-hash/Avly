import { useEffect, useRef, useState } from "react";
import TopNav from "../../components/common/TopNav";
import TimelineNotice from "./TimelineNotice";
import TimelineAxis from "./TimelineAxis";
import TimelineControls from "./TimelineControls";
import LawPageLink from "./LawPageLink";
import { getTimelineColor, getTimelinePosition } from "./timelineColors";
import useTimelineWheel from "./useTimelineWheel";
import "./Time.css";

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
  },
  {
    id: "m0",
    label: "충돌 시점",
    time: 11.9,
    summary: "물리적 접촉 좌표 포착",
    tag: "충돌 좌표 확정",
    title: "우측 전면 범퍼-상대 좌측 후미 불가항력 접촉",
    hud: "IMPACT FORCE 1.48G",
    tone: "impact",
  },
];

const LAST = MOMENTS.length - 1;
const stamp = (t) => `00:${t.toFixed(2).padStart(5, "0")}`;
const two = (n) => String(n).padStart(2, "0");

export default function Time() {
  const stageRef = useRef(null);
  const videoRef = useRef(null);
  const inputRef = useRef(null);
  const [active, setActive] = useState(0);
  const [videoUrl, setVideoUrl] = useState("");
  const [videoName, setVideoName] = useState("");

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const goTo = (i) => {
    const idx = Math.max(0, Math.min(LAST, i));
    setActive(idx);
    const video = videoRef.current;
    if (video && video.readyState >= HTMLMediaElement.HAVE_METADATA && Number.isFinite(video.duration)) {
      video.currentTime = Math.min(MOMENTS[idx].time, Math.max(0, video.duration - 0.05));
    }
  };

  useTimelineWheel(stageRef, active, MOMENTS.length, goTo);

  const loadVideo = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setVideoUrl(URL.createObjectURL(file));
    setVideoName(file.name);
    event.target.value = "";
  };

  useEffect(() => {
    if (!videoUrl) return undefined;
    return () => URL.revokeObjectURL(videoUrl);
  }, [videoUrl]);

  const syncVideoToMoment = () => {
    const video = videoRef.current;
    if (video && Number.isFinite(video.duration)) {
      video.currentTime = Math.min(MOMENTS[active].time, Math.max(0, video.duration - 0.05));
    }
  };

  const m = MOMENTS[active];
  const frameColor = getTimelineColor(getTimelinePosition(MOMENTS, m.time));

  return (
    <div className="tl">
      <TopNav active="타임라인" theme="dark" />

      <section className="tl-stage" ref={stageRef}>
        {/* 왼쪽: 제목 · 비율 · 지금 보고 있는 시점 */}
        <div className="tl-side" style={{ "--accent": frameColor }}>
          <h1>
            사고 순간
            <br />
            <span className="tl-h1-accent">타임라인</span>
          </h1>
          <div className={`tl-now ${m.tone || ""}`}>
            <div className="tl-now-content" key={m.id} aria-live="polite">
              <p className="tl-now-step">
                STEP {two(active + 1)} · <span className="tl-mono">{stamp(m.time)}</span>
              </p>
              <p className="tl-now-label">{m.summaryLabel || m.label}</p>
            </div>
            <div className="tl-now-row">
              <p className="tl-now-text" key={`summary-${m.id}`} aria-live="polite">{m.summary}</p>
              <TimelineControls active={active} last={LAST} onSelect={goTo} />
            </div>
          </div>
        </div>

        {/* 오른쪽: 영상 화면 · 시간축 */}
        <div className="tl-right">
          <div className="tl-video-panel" style={{ "--tl-frame-color": frameColor }}>
            <div className={`tl-player ${m.tone || ""}`}>
              {videoUrl ? (
                <video
                  ref={videoRef}
                  className="tl-video"
                  src={videoUrl}
                  controls
                  onLoadedMetadata={syncVideoToMoment}
                  aria-label={`${m.label} 블랙박스 영상`}
                />
              ) : (
                <>
                  <Scene id={m.id} />
                  <div className="tl-player-prompt">
                    <p>선택한 시점의 영상</p>
                    <button type="button" className="tl-upload" onClick={() => inputRef.current?.click()}>
                      블랙박스 영상 선택
                    </button>
                  </div>
                </>
              )}
              <input
                ref={inputRef}
                className="tl-file-input"
                type="file"
                accept="video/mp4,video/quicktime,video/x-msvideo,.mp4,.mov,.avi"
                onChange={loadVideo}
                aria-label="블랙박스 영상 파일 선택"
              />
              <span className="tl-rec">REC</span>
              <figcaption className="tl-hud tl-mono">
                T: {stamp(m.time)} · {m.hud}
              </figcaption>
            </div>
            {videoName && <p className="tl-video-name">{videoName}</p>}
          </div>
          <div className="tl-analysis">
            <div className="tl-selected-moment">
              <p className="tl-when">
                <span className="tl-mono">[{stamp(m.time)}]</span>
                <span className="tl-tag">{m.tag}</span>
              </p>
              <h2>{m.title}</h2>
            </div>

            {/* 실제 시각 비율대로 놓인 시간축: 지나온 구간이 채워짐 */}
            <TimelineAxis moments={MOMENTS} active={active} onSelect={goTo} />
          </div>
        </div>
        <div className="tl-footer">
          <LawPageLink />
          <TimelineNotice />
        </div>
      </section>
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
    <svg className="tl-scene" viewBox="0 0 320 180" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <defs>
        <linearGradient id={`sky-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--bg)" />
          <stop offset="1" stopColor="var(--tl-scene-sky-bottom)" />
        </linearGradient>
      </defs>
      <rect width="320" height="72" fill={`url(#sky-${id})`} />
      <rect y="70" width="320" height="110" fill="var(--panel)" />
      <polygon points="146,70 174,70 330,180 -10,180" fill="var(--tl-scene-sky-bottom)" />
      <path d="M151 70 L40 180 M169 70 L280 180" stroke="#b8b8c4" strokeWidth="1.5" opacity="0.55" />
      <path d="M160 70 L160 180" stroke="#e2b25a" strokeWidth="1.5" opacity="0.7" />
      <path d="M155 70 L100 180 M165 70 L220 180" stroke="#fff" strokeWidth="1.2" strokeDasharray="7 9" opacity="0.35" />

      {id === "m5" && (
        <>
          <Car x={138} y={98} s={0.42} />
          <path d="M132 176 L136 106" stroke="var(--accent)" strokeWidth="1.2" strokeDasharray="3 4" />
          <text x="142" y="146" fill="var(--accent)" fontSize="10" fontWeight="700">
            35m
          </text>
        </>
      )}
      {id === "m3" && (
        <>
          <defs>
            <marker id={`arrow-${id}`} viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0 0 L10 5 L0 10 z" fill="var(--accent)" />
            </marker>
          </defs>
          <Car x={212} y={112} s={0.68} rotate={-14} />
          <rect x="184" y="88" width="58" height="38" fill="none" stroke="var(--accent)" strokeWidth="1.3" strokeDasharray="4 3" />
          <path className="tl-arrow" d="M196 128 Q170 140 150 150" stroke="var(--accent)" strokeWidth="2" fill="none" markerEnd={`url(#arrow-${id})`} />
          <text x="186" y="82" fill="var(--accent)" fontSize="9" fontWeight="700">
            깜빡이 OFF
          </text>
        </>
      )}
      {id === "m1" && (
        <>
          <Car x={150} y={132} s={1.15} brake />
          <path d="M150 178 L150 150" stroke="var(--accent)" strokeWidth="1.2" strokeDasharray="3 3" />
          <text x="156" y="172" fill="var(--accent)" fontSize="10" fontWeight="700">
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
