import "./CaseBasisNotice.css";

const DEFAULT_NOTICE =
  "에블리는 손해보험협회 과실비율 인정기준과 판례 요약을 참고해 과실 비율을 안내하는 AI 참고 서비스예요. 확정한 비율이 아니며 법적 효력이 없고, 최종 판단은 보험사 합의나 법원 판결에 따릅니다.";

export default function CaseBasisNotice({ children = DEFAULT_NOTICE, className = "" }) {
  return (
    <footer className={`case-basis-notice ${className}`} aria-label="판례 기준 안내">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 3 5 6v5c0 4.5 3 8.5 7 10 4-1.5 7-5.5 7-10V6z" />
        <path d="m9.5 12 2 2 3.5-4" />
      </svg>
      <p>{children}</p>
    </footer>
  );
}
