// 결과가 어떤 상태인지(확정, 일부만 반영, 기본값만, 확정 불가) 쉬운 말로 알려 주고,
// 확인하지 못한 가감요소가 있으면 무엇인지 보여 준다.
export default function StatusNotice({ text, pending = [] }) {
  if (!text && pending.length === 0) return null;
  return (
    <div className="ar-status" role="note">
      {text && <p>{text}</p>}
      {pending.length > 0 && (
        <>
          <h3>아직 확인하지 못한 가감요소</h3>
          <ul>
            {pending.map((item) => (
              <li key={`${item.who}-${item.factor}`}>
                <strong>{item.title}</strong> <span>({item.effect})</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
