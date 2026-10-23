import useCalculating from "../hooks/useCalculating";

// AI 예상 과실 비율: 작은 제목 → 큰 "20 : 80" + 오른쪽 범례 → 아래 얇은 비율 막대
// 페이지에 들어오면 "산정 중"(숫자가 뒤섞이고 막대에 빛이 훑음) → "산정 완료"(예상 비율에 멈추며 튀어 오름)
// (들어올 때 한 번만, 스크롤로는 바뀌지 않음)
export default function FinalRatio({ mine, other, label = "AI 예상 과실 비율", confirmed = true }) {
  const { done, ratio } = useCalculating([mine, other]);
  const [shownMine, shownOther] = ratio;

  return (
    <div
      className={done ? "ar-factor-summary is-done" : "ar-factor-summary is-calculating"}
      aria-busy={!done}
      aria-label={done ? `${label} 내 과실 ${mine}%, 상대 과실 ${other}%` : "과실 비율 산정 중"}
    >
      <p className="ar-factor-kicker">
        {done ? (
          <>
            {label}
            {confirmed && (
              <span className="ar-factor-done">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m5 12.5 4.5 4.5L19 7.5" />
                </svg>
                산정 완료
              </span>
            )}
          </>
        ) : (
          <>
            과실 비율 산정 중
            <span className="ar-factor-dots" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
          </>
        )}
      </p>
      <div className="ar-factor-ratios" aria-hidden="true">
        {/* key가 바뀌면 다시 그려지며 멈추는 순간 튀어 오름 */}
        <strong key={done ? "done" : "calc"} className="ar-factor-big">
          <span className="ar-factor-mine">{shownMine}</span>
          <span className="ar-factor-colon">:</span>
          <span className="ar-factor-other">{shownOther}</span>
        </strong>
        <ul className="ar-factor-legend">
          <li className="ar-factor-mine"><i />내 과실 <b>{shownMine}%</b></li>
          <li className="ar-factor-other"><i />상대 과실 <b>{shownOther}%</b></li>
        </ul>
      </div>
      {/* 산정 중엔 비어 있다가 완료되면 내 과실만큼 차오름 */}
      <div className="ar-factor-bar" aria-hidden="true">
        <span style={{ width: done ? `${mine}%` : 0 }} />
        <span />
      </div>
    </div>
  );
}
