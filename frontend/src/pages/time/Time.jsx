import { useEffect, useMemo, useRef, useState } from "react";
import AnalysisGate from "../common/components/AnalysisGate";
import TopNav from "../common/components/TopNav";
import { toMoments } from "../../api/adapters";
import TimelineNotice from "./components/TimelineNotice";
import TimelineAxis from "./components/TimelineAxis";
import TimelineControls from "./components/TimelineControls";
import LawPageLink from "./components/LawPageLink";
import EmptyTimeline from "./components/EmptyTimeline";
import VideoPanel from "./components/VideoPanel";
import { stamp, two } from "./timeFormat";
import useTimelineVideo from "./hooks/useTimelineVideo";
import { getTimelineColor, getTimelinePosition } from "./timelineColors";
import useTimelineWheel from "./hooks/useTimelineWheel";
import "./Time.css";

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
  if (moments.length === 0) return <EmptyTimeline analysisId={analysisId} />;
  return <Moments moments={moments} analysisId={analysisId} session={session} />;
}

function Moments({ moments, analysisId, session }) {
  const LAST = moments.length - 1;
  const stageRef = useRef(null);
  const [active, setActive] = useState(0);
  const { videoRef, inputRef, source, videoName, seek, loadVideo } = useTimelineVideo(session);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const goTo = (i) => {
    const idx = Math.max(0, Math.min(LAST, i));
    setActive(idx);
    seek(moments[idx].time);
  };

  useTimelineWheel(stageRef, active, moments.length, goTo);

  const syncVideoToMoment = () => seek(moments[active].time);

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
          <VideoPanel
            moment={m}
            frameColor={frameColor}
            source={source}
            videoRef={videoRef}
            inputRef={inputRef}
            videoName={videoName}
            onLoadedMetadata={syncVideoToMoment}
            onLoadFile={loadVideo}
          />
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
