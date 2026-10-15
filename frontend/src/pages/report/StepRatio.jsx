import { useAnimatedNumber } from "./useScrollStep";

// 가감요소 왼쪽의 작은 과실 비율 박스: 지금 단계의 카드 옆으로 미끄러져 내려가며 비율이 바뀜
// offset = 지금 단계 카드의 목록 안 세로 위치(px)
export default function StepRatio({ steps, activeIndex, offset }) {
  const [mine, other] = steps[activeIndex].ratio;
  const change = activeIndex > 0 ? mine - steps[activeIndex - 1].ratio[0] : 0;
  const shownMine = useAnimatedNumber(mine);
  const shownOther = useAnimatedNumber(other);

  return (
    <div className="ar-step-col">
      <div className="ar-step-ratio" style={{ "--ar-step-y": `${offset}px` }} aria-live="polite">
        <p className="ar-step-label">
          {activeIndex === 0 ? "기본 기준" : `${activeIndex + 1}단계 반영`}
          {change !== 0 && (
            // key가 바뀌면 다시 그려지며 살짝 튀어 오름
            <span key={activeIndex} className="ar-step-change">
              {change < 0 ? "▼" : "▲"}
              {Math.abs(change)}%p
            </span>
          )}
        </p>
        <p className="ar-step-numbers">
          <span className="ar-factor-mine">{shownMine}</span>
          <span className="ar-factor-colon" aria-hidden="true">:</span>
          <span className="ar-factor-other">{shownOther}</span>
        </p>
        <div className="ar-step-bar" aria-hidden="true">
          <span style={{ width: `${mine}%` }} />
          <span />
        </div>
      </div>
    </div>
  );
}
