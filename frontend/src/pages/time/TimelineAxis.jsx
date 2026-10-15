import { getTimelineColor, getTimelinePosition } from "./timelineColors";

const stamp = (time) => `00:${time.toFixed(2).padStart(5, "0")}`;

export default function TimelineAxis({ moments, active, onSelect }) {
  const position = (time) => getTimelinePosition(moments, time);
  const progress = position(moments[active].time);

  return (
    <div className="tl-axis">
      <span className="tl-axis-line" />
      <span className="tl-axis-fill" style={{ clipPath: `inset(0 ${100 - progress}% 0 0)` }} />
      {moments.map((moment, index) => {
        const offset = position(moment.time);
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
