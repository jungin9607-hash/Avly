import "./SituationCheckNotice.css";

// 사용자가 고른 사고 상황이 AI 가 영상에서 본 내용과 어긋날 때만 보여 주는 안내. check 는 toSituationCheck() 의 결과(없으면 아무것도 그리지 않는다).
export default function SituationCheckNotice({ check, className = "" }) {
  if (!check) return null;
  return (
    <aside className={`situation-check ${className}`} role="note">
      <strong>{check.title}</strong>
      <p>{check.body}</p>
      <ul>
        {check.lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </aside>
  );
}
