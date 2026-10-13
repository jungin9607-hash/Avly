import { useEffect, useId, useRef } from "react";
import "./Modal.css";

/* 팝업 공통 틀: 맨 위 단계 막대 + 흰 머리말 + 흰 본문
 * progress: [현재 단계, 전체 단계] (예: [1, 2]) */
export default function ModalShell({ badge, title, desc, progress, onClose, children }) {
  const titleId = useId();
  const dialogRef = useRef(null);

  // 부모가 렌더마다 새 함수를 넘겨도 아래 효과가 다시 돌지 않도록 ref로 보관
  const closeRef = useRef(onClose);
  useEffect(() => {
    closeRef.current = onClose;
  }, [onClose]);

  // Esc로 닫기, 뒤 화면 스크롤 잠금, 열리면 팝업에 포커스
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && closeRef.current();
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialogRef.current?.focus();
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, []);

  return (
    <div className="md-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="md" role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} ref={dialogRef}>
        {progress && (
          <ol className="md-progress" aria-label={`전체 ${progress[1]}단계 중 ${progress[0]}단계`}>
            {Array.from({ length: progress[1] }, (_, i) => (
              <li key={i} className={i < progress[0] ? "on" : ""} />
            ))}
          </ol>
        )}
        <header className="md-head">
          <button type="button" className="md-close" aria-label="닫기" onClick={onClose}>
            ×
          </button>
          <div className="md-head-top">
            {progress && (
              <span className="md-step">
                STEP <b>{progress[0]}</b> / {progress[1]}
              </span>
            )}
            {badge && <span className="md-badge">{badge}</span>}
          </div>
          <h2 id={titleId}>{title}</h2>
          {desc && <p>{desc}</p>}
        </header>
        {children}
      </div>
    </div>
  );
}
