function FinalRatio({ initial, mine, other }) {
  const reduction = initial - mine;
  return (
    <div className="ar-factor-summary" aria-label="최종 과실 비율">
      <div className="ar-factor-ratios">
        <p className="ar-factor-mine"><i aria-hidden="true" />내 과실 <strong>{mine}%</strong></p>
        <p className="ar-factor-other"><strong>{other}%</strong> 상대 과실<i aria-hidden="true" /></p>
      </div>
      <div className="ar-factor-bar" role="img" aria-label={`내 과실 ${mine}%, 상대 과실 ${other}%`}>
        <span style={{ flex: mine }}>{mine}%</span>
        <span style={{ flex: other }}>{other}%</span>
      </div>
      <p className="ar-factor-note">기본 과실({initial}%) 대비 {Math.abs(reduction)}%p {reduction >= 0 ? '감산' : '가산'} 인정</p>
    </div>
  );
}

function FactorCard({ factor, index }) {
  return (
    <li className="ar-factor-card">
      <div className="ar-factor-body">
        <div className="ar-factor-heading">
          <div className="ar-factor-title">
            <span className="ar-factor-number">{index + 1}</span>
            <h3>{factor.title}</h3>
          </div>
          <span className="ar-factor-tag">{factor.tag}</span>
        </div>
        <p className="ar-factor-description">{factor.body}</p>
      </div>
    </li>
  );
}

export default function AdjustmentSteps({ steps }) {
  const [mine, other] = steps[steps.length - 1].ratio;
  return (
    <div className="ar-factor-overview">
      <FinalRatio initial={steps[0].ratio[0]} mine={mine} other={other} />
      <header className="ar-factor-header">
        <h2>왜 {mine}:{other}으로 분석됐나요?</h2>
        <span>단계별 과실 조정 요인</span>
      </header>
      <ol className="ar-factor-list" aria-label="과실 조정 요인">
        {steps.map((factor, index) => <FactorCard key={factor.title} factor={factor} index={index} />)}
      </ol>
    </div>
  );
}
