import { useEffect, useRef } from "react";
import { compareNote } from "../lawContent";
import { Quote } from "./CaseDetails";

// 선택한 판례와 내 사고의 공통점·차이점 정밀 대조 팝업
export default function CompareModal({ caseItem, onClose }) {
  const dialogRef = useRef(null);

  useEffect(() => {
    dialogRef.current?.focus();

    const onKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    // 팝업이 떠 있는 동안 뒤 화면은 스크롤되지 않게
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose]);

  const { common, differences } = caseItem.comparison;

  return (
    // 바깥 어두운 영역을 누르면 닫힘
    <div className="law-modal-backdrop" onClick={onClose}>
      <div
        ref={dialogRef}
        className="law-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="law-modal-title"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="law-modal-header">
          <div>
            <p className="law-modal-kicker">
              {caseItem.date} 판결 · {caseItem.matchLabel}
            </p>
            <h2 id="law-modal-title">
              내 사고 <span className="law-modal-vs">vs</span> {caseItem.court} 판례 정밀 대조
            </h2>
          </div>
        </header>

        {/* 일반적인 팝업 닫기: 오른쪽 위 구석의 작은 × (바탕 없이 선 아이콘만) */}
        <button type="button" className="law-modal-close" aria-label="닫기" onClick={onClose}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 6l12 12M18 6 6 18" />
          </svg>
        </button>

        {caseItem.note && <p className="law-modal-note">{compareNote(caseItem.note)}</p>}

        <div className="law-modal-columns">
          <CompareColumn tone="common" title="공통점" items={common} />
          <CompareColumn tone="diff" title="차이점" items={differences} />
        </div>

        <footer className="law-modal-footer">
          <button type="button" className="law-modal-confirm" onClick={onClose}>
            확인
          </button>
        </footer>
      </div>
    </div>
  );
}

// 팝업 안 공통점 / 차이점 한 열: 앞 세로 막대 + 흰 굵은 제목 + 옅은 개수
// tone: "common" | "diff" (막대 색 구분)
function CompareColumn({ tone, title, items }) {
  return (
    <section className={`law-modal-col is-${tone}`}>
      <h3>
        {title}
        <span className="law-modal-count">{items.length}</span>
      </h3>
      <ul>
        {items.map((item) => (
          <li key={item.label}>
            <strong>{item.label}</strong>
            <p>
              <RichText parts={item.text} />
            </p>
            <Quote text={item.quote} />
          </li>
        ))}
      </ul>
    </section>
  );
}

// 문장 조각 배열을 그림: 문자열은 그대로, { strong: "..." }는 굵게
function RichText({ parts }) {
  return parts.map((part, i) =>
    typeof part === "string" ? part : <strong key={i}>{part.strong}</strong>
  );
}
