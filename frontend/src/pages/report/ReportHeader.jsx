// 화면 맨 위: 큰 제목 + 그 아래 설명 문장 옆에 사고 정보를 키워드 칩으로
export default function ReportHeader({ content }) {
  return (
    <header className="ar-report-header">
      <h1>{content.title}</h1>
      <div className="ar-report-sub">
        {content.desc && <p className="ar-report-desc">{content.desc}</p>}
        <ul className="ar-report-keywords" aria-label="사고 정보">
          {content.keywords.map((keyword) => (
            <li key={keyword}>{keyword}</li>
          ))}
        </ul>
      </div>
    </header>
  );
}
