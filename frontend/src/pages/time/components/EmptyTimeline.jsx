import TopNav from "../../common/components/TopNav";
import LawPageLink from "./LawPageLink";
import TimelineNotice from "./TimelineNotice";

/* 영상에서 표시할 사고 장면을 찾지 못했을 때 */
export default function EmptyTimeline({ analysisId }) {
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
