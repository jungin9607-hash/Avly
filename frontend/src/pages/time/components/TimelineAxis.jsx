import { getTimelineColor, getTimelinePosition } from "../timelineColors";

const stamp = (time) => `00:${time.toFixed(2).padStart(5, "0")}`;

export default function TimelineAxis({ moments, active, onSelect }) {
  // 위치는 순서대로 고르게 나눈 값(position)을 우선 쓴다. 없으면 시각 비율로 계산한다.
  const where = (moment) => moment.position ?? getTimelinePosition(moments, moment.time);
  const progress = where(moments[active]);

  return (
    <div className="tl-axis">
      <span className="tl-axis-line" />
      <span className="tl-axis-fill" style={{ clipPath: `inset(0 ${100 - progress}% 0 0)` }} />
      {moments.map((moment, index) => {
        const offset = where(moment);
        return (
          <button
            key={moment.id}
            type="button"
            aria-label={`${moment.label} ${stamp(moment.time)}`}
            aria-current={index === active ? "step" : undefined}
            className={`tl-axis-dot ${moment.tone || ""} ${index <= active ? "is-past" : ""} ${
              index === 0 ? "is-first" : ""
            } ${index === moments.length - 1 ? "is-last" : ""}`}
            style={{
              left: `${offset}%`,
              "--tl-dot-color": getTimelineColor(offset),
            }}
            onClick={() => onSelect(index)}
          >
            <em className="tl-mono">{stamp(moment.time)}</em>
            <small>{moment.label}</small>
          </button>
        );
      })}
    </div>
  );
}
