// "상세 보기"를 펼치면 위에서 아래로 차례로 쭉 나오는 판례 설명
// 결과 한 문장(숫자 강조) + 개요 → 사고 경위 → 과실비율 산정(기본 → 가감 → 최종) → 법원 판단 요지 → 적용 법령
// open: 펼침 여부 (닫혀 있어도 그려 두고 높이만 0으로 접어, 펼칠 때 부드럽게 내려옴)
export default function CaseDetails({ item, open }) {
  const { overview, timeline, ratioBasis, rulingPoints, laws } = item.details;
  const [mine, other] = item.ratio.split(":").map((v) => v.trim());

  return (
    <div className={`law-details-collapse${open ? " is-open" : ""}`} inert={!open}>
      <div className="law-details-clip">
        {/* 읽는 영역이라 눌러도 카드 선택(on/off)이 바뀌지 않게 */}
        <div className="law-case-details" onClick={(e) => e.stopPropagation()}>
          <p className="law-details-headline">
            법원은 상대 차량 과실을 <em className="is-other">{other}%</em>, 내 차 과실을{" "}
            <em className="is-mine">{mine}%</em>로 인정했습니다.
          </p>
          <p className="law-details-overview">{overview}</p>

          <DetailSection title="사고 경위">
            <ol className="law-details-steps">
              {timeline.map((step) => (
                <li key={step.time}>
                  <span className="law-details-time">{step.time}</span>
                  <p>{step.text}</p>
                </li>
              ))}
            </ol>
          </DetailSection>

          <DetailSection title="과실비율 산정">
            {/* 기본 비율 → 가감(이유와 함께) → 최종, 위에서 아래로 한 흐름
                상대 과실 가산은 딥 네이비, 내 차 가산은 밝은 블루 */}
            <ol className="law-details-flow">
              <li>
                <span className="law-flow-badge">기본</span>
                <p>
                  <strong>{ratioBasis.baseLabel}</strong>
                </p>
                <b className="law-flow-ratio">{ratioBasis.base}</b>
              </li>
              {ratioBasis.adjustments.map((adj) => (
                <li key={adj.label}>
                  <span className={`law-flow-badge is-${adj.side}`}>
                    {adj.side === "other" ? "상대" : "내 차"} ▲{adj.value}
                  </span>
                  <p>
                    <strong>{adj.label}</strong> — {adj.note}
                  </p>
                </li>
              ))}
              <li className="is-result">
                <span className="law-flow-badge">최종</span>
                <p>
                  <strong>내 차 : 상대</strong>
                </p>
                <b className="law-flow-ratio">
                  <span className="is-mine">{mine}</span> : <span className="is-other">{other}</span>
                </b>
              </li>
            </ol>
          </DetailSection>

          <DetailSection title="법원 판단 요지">
            <ul className="law-details-points">
              {rulingPoints.map((point) => (
                <li key={point}>
                  <CheckIcon />
                  {point}
                </li>
              ))}
            </ul>
          </DetailSection>

          <DetailSection title="적용 법령">
            <ul className="law-details-laws">
              {laws.map((law) => (
                <li key={law.name}>
                  <strong>{law.name}</strong>
                  <p>{law.gist}</p>
                </li>
              ))}
            </ul>
          </DetailSection>

          <p className="law-details-source">판결 요약 · 예시 데이터</p>
        </div>
      </div>
    </div>
  );
}

// 소제목(왼쪽 블루 점) + 내용, 위쪽 옅은 구분선
function DetailSection({ title, children }) {
  return (
    <section className="law-details-section">
      <h4>{title}</h4>
      {children}
    </section>
  );
}

// 블루 체크 표시 (원 없이 체크만, 글자 "✓"는 글꼴 기준선 때문에 아래로 처져서 SVG로 그려 가운데에 맞춤)
export function CheckIcon({ className = "law-check" }) {
  return (
    <svg className={className} viewBox="0 0 20 20" aria-hidden="true">
      <path d="m4 10.5 4 4L16 6" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
