export default function ReportHeader({ reportCode, accidentType }) {
  return (
    <header className="ar-report-header">
      <div className="ar-report-meta">
        <span>식별 코드 <b>{reportCode}</b></span>
        <span>사고 유형: {accidentType}</span>
      </div>
      <h1>과실 분석 결과</h1>
    </header>
  );
}
