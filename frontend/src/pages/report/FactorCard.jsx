import Disclosure from "./Disclosure";

// 과실 조정 요인 카드: 큰 번호 원 | 쉬운 말 제목·설명 + "법적 근거 자세히 보기"(누르면 펼침) | 오른쪽 태그
// state: done(이미 반영) · active(지금 반영 중) · upcoming(아직)
export default function FactorCard({ factor, index, state }) {
  return (
    <li className={`ar-factor-card is-${state}`} aria-current={state === "active" ? "step" : undefined}>
      <span className="ar-factor-number">{index + 1}</span>
      <div className="ar-factor-body">
        <div className="ar-factor-heading">
          <h3>{factor.title}</h3>
          {/* 첫 단계(출발점)는 회색, 가감 단계는 파란 테두리 */}
          <span className={index === 0 ? "ar-factor-tag is-base" : "ar-factor-tag"}>{factor.tag}</span>
        </div>
        <p className="ar-factor-description">{factor.body}</p>

        {factor.legal?.length > 0 && (
          <Disclosure label="법적 근거 자세히 보기" openLabel="법적 근거 접기">
            <ul className="ar-factor-legal">
              {factor.legal.map((item) => (
                <li key={item.name}>
                  <strong>{item.name}</strong>
                  <p>{item.text}</p>
                </li>
              ))}
            </ul>
          </Disclosure>
        )}
      </div>
    </li>
  );
}
