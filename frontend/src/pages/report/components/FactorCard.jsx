import Disclosure from "./Disclosure";

// 과실 조정 요인 카드: 큰 번호 원 | 쉬운 말 제목·설명 + "법적 근거 자세히 보기"(누르면 펼침) | 오른쪽 태그
// state: done(이미 반영) · active(지금 반영 중) · upcoming(아직)
// 선택 안 된 카드는 아무 곳이나 누르면 그 카드가 선택됨 (onSelect)
//   이때 "법적 근거 자세히 보기"를 눌러도 펼치지 않고 선택만 함 (선택된 뒤 다시 누르면 펼침)
export default function FactorCard({ factor, index, state, onSelect }) {
  const selectable = state !== "active" && onSelect;
  return (
    <li
      className={`ar-factor-card is-${state}${selectable ? " is-selectable" : ""}`}
      aria-current={state === "active" ? "step" : undefined}
      onClickCapture={(e) => {
        if (!selectable) return;
        e.stopPropagation(); // 안쪽 펼치기 버튼까지 전달하지 않음
        onSelect(index);
      }}
    >
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
