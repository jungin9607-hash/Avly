import "./LegalNotice.css";

// 분석 결과 · 타임라인 등 여러 화면 하단에 공통으로 들어가는 법적 고지
// tone="dark": 어두운 배경 화면용
export default function LegalNotice({ tone }) {
  return (
    <section className={tone === "dark" ? "ln ln-dark" : "ln"}>
      <svg
        width="22"
        height="22"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M12 3 5 6v5c0 4.5 3 8.5 7 10 4-1.5 7-5.5 7-10V6z" />
        <path d="m9.5 12 2 2 3.5-4" />
      </svg>
      <div>
        <h3>법적 책임 고지 및 안내</h3>
        <p>
          본 서비스는 AI 영상 분석 엔진 및 대법원·손해보험협회 과실비율 인정기준 판례 데이터를 기반으로 제공되는
          객관적 참고자료이며, 변호사법 제109조에 따른 법률적 대리 행위 또는 확정 판결을 대신하지 않습니다.
        </p>
      </div>
      {/* TODO: 판례 기준 가이드라인 화면과 연결 */}
      <button type="button" className="ln-btn">
        판례 기준 가이드라인
      </button>
    </section>
  );
}
