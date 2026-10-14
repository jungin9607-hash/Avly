import { useEffect } from "react";
import ModalShell from "./ModalShell";

export default function AnalysisProgressModal({ step, description, onComplete, onClose }) {
  useEffect(() => {
    const timeoutId = window.setTimeout(onComplete, 1800);
    return () => window.clearTimeout(timeoutId);
  }, [onComplete]);

  return (
    <ModalShell
      title="영상 분석 중"
      desc={description}
      progress={[step, 5]}
      onClose={onClose}
    >
      <div className="md-analysis" role="status" aria-live="polite">
        <span className="md-analysis-spinner" aria-hidden="true" />
        <p>잠시만 기다려 주세요</p>
        <div className="md-analysis-track" aria-hidden="true">
          <span />
        </div>
      </div>
    </ModalShell>
  );
}
