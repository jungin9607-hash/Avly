import { useEffect, useMemo, useRef, useState } from "react";
import AnalysisGate from "../../components/common/AnalysisGate";
import TopNav from "../../components/common/TopNav";
import { api } from "../../api/client";
import { toMoments } from "../../api/adapters";
import TimelineNotice from "./TimelineNotice";
import TimelineAxis from "./TimelineAxis";
import TimelineControls from "./TimelineControls";
import LawPageLink from "./LawPageLink";
import { getTimelineColor, getTimelinePosition } from "./timelineColors";
import useTimelineWheel from "./useTimelineWheel";
import "./Time.css";

const stamp = (t) => `00:${t.toFixed(2).padStart(5, "0")}`;
const two = (n) => String(n).padStart(2, "0");

// 사고 타임라인. 서버가 영상에서 찾은 구간(시작~끝 초)을 시간순으로 보여 주고, 영상이 있으면 그 시점으로 이동한다.
export default function Time({ analysisId }) {
  return (
    <AnalysisGate analysisId={analysisId} active="타임라인" theme="dark">
      {({ analysis, session }) => <TimeView result={analysis.result} analysisId={analysisId} session={session} />}
    </AnalysisGate>
  );
}

function TimeView({ result, analysisId, session }) {
  const moments = useMemo(() => toMoments(result), [result]);
  if (moments.length === 0) {
    return (
      <div className="tl">
        <TopNav active="타임라인" theme="dark" />
        <section className="tl-stage">
          <div className="tl-side">
            <h1>
              사고 순간
              <br />
              <span className="tl-h1-accent">타임라인</span>
            </h1>
            <p className="tl-now-text">영상에서 표시할 사고 장면을 찾지 못했어요.</p>
          </div>
          <div className="tl-footer">
            <LawPageLink analysisId={analysisId} />
            <TimelineNotice />
          </div>
        </section>
      </div>
    );
  }
  return <Moments moments={moments} analysisId={analysisId} session={session} />;
}

function Moments({ moments, analysisId, session }) {
  const LAST = moments.length - 1;
  const stageRef = useRef(null);
  const videoRef = useRef(null);
  const inputRef = useRef(null);
  const [active, setActive] = useState(0);
  const [videoUrl, setVideoUrl] = useState(""); // 사용자가 직접 고른 영상(영상을 보관하지 않은 경우의 대안)
  const [videoName, setVideoName] = useState("");
  const [serverVideo, setServerVideo] = useState(null); // 번호판·사람을 가린 영상 (보관 동의한 경우)

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  // 서버에 보관된 비식별 영상이 있으면 그 영상을 쓴다. 서명 주소는 짧게 유효하므로 화면에 들어올 때 받는다.
  useEffect(() => {
    let cancelled = false;
    api.videoUrl(session.accidentId, { sessionId: session.sessionId }).then(
      (url) => !cancelled && setServerVideo(url),
      () => {},
    );
    return () => {
      cancelled = true;
    };
  }, [session.accidentId, session.sessionId]);

  const seek = (time) => {
    const video = videoRef.current;
    if (video && video.readyState >= HTMLMediaElement.HAVE_METADATA && Number.isFinite(video.duration)) {
      video.currentTime = Math.min(time, Math.max(0, video.duration - 0.05));
    }
  };

  const goTo = (i) => {
    const idx = Math.max(0, Math.min(LAST, i));
    setActive(idx);
    seek(moments[idx].time);
  };

  useTimelineWheel(stageRef, active, moments.length, goTo);

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

  const syncVideoToMoment = () => seek(moments[active].time);
  const source = videoUrl || serverVideo;

  const m = moments[active];
  const frameColor = getTimelineColor(m.position ?? getTimelinePosition(moments, m.time));

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
              {source ? (
                <video
                  ref={videoRef}
                  className="tl-video"
                  src={source}
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
            <TimelineAxis moments={moments} active={active} onSelect={goTo} />
          </div>
        </div>
        <div className="tl-footer">
          <LawPageLink analysisId={analysisId} />
          <TimelineNotice />
        </div>
      </section>
    </div>
  );
}

/* ---------- 영상이 없을 때 보여 주는 도로 배경 (실제 장면이 아니다) ---------- */

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
    </svg>
  );
}
