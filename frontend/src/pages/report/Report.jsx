import { useEffect, useRef, useState } from "react";
import TopNav from "../../components/common/TopNav";
import useNavigationBackdrop from "../../components/common/useNavigationBackdrop";
import ReportNotice from "./ReportNotice";
import AdjustmentSteps from "./AdjustmentSteps";
import ReportHeader from "./ReportHeader";
import ReportActions, { TimelineLink } from "./ReportActions";
import {
  REPORT_HEADER,
  FACTOR_HEADER,
  STEPS,
  REPORT_ACTIONS,
} from "./reportContent";
import { useScrollStep } from "./useScrollStep";
import "./Report.css";

export default function Report() {
  const [toast, setToast] = useState("");
  const reportRef = useRef(null);
  useNavigationBackdrop(reportRef);
  const resultRef = useRef(null);
  const { step: activeStep, pinned, goToStep } = useScrollStep(resultRef, STEPS.length);

  useEffect(() => {
    const report = reportRef.current;
    const updateWidth = () => report.style.setProperty("--ar-viewport-width", `${report.clientWidth}px`);
    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    observer.observe(report);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  // 증거 구간이 화면 아래 40% 선 위로 올라오면 "사고 타임라인 바로가기"를 보여 줌 (위로 올라가면 다시 숨김)
  const evidenceRef = useRef(null);
  const [evidenceInView, setEvidenceInView] = useState(false);
  useEffect(() => {
    const io = new IntersectionObserver(([entry]) => setEvidenceInView(entry.isIntersecting), {
      rootMargin: "0px 0px -40% 0px",
    });
    io.observe(evidenceRef.current);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(""), 2200);
    return () => clearTimeout(id);
  }, [toast]);

  const share = async () => {
    const data = { title: "에블리 과실 분석 결과 · AV-24901", url: window.location.href };
    try {
      if (navigator.share) {
        await navigator.share(data);
      } else {
        await navigator.clipboard.writeText(data.url);
        setToast("결과 링크를 복사했어요");
      }
    } catch {
      // 사용자가 공유 창을 닫은 경우 등은 조용히 무시
    }
  };

  return (
    <div className="ar" ref={reportRef}>
      {/* 메뉴 바는 유사 판례와 같은 기본 스타일 (색은 Report.css에서 맞춤) */}
      <TopNav active="분석 결과" />

      <main className="ar-main">
        {/* 최종 과실 비율과 전체 조정 요인을 함께 표시 */}
        {/* 넓은 화면: 안쪽(pin)이 화면에 고정된 채 아래 track 길이만큼 스크롤하면
            기본 기준 → 조정 요인 → 최종 순으로 과실 비율이 바뀜 */}
        <section
          ref={resultRef}
          className={`ar-section ar-report-page ar-result-page${pinned ? " is-pinned" : ""}`}
          style={{ "--ar-step-count": STEPS.length }}
        >
          <div className="ar-result-pin">
            <ReportHeader content={REPORT_HEADER} />
            <AdjustmentSteps
              steps={STEPS}
              header={FACTOR_HEADER}
              activeIndex={activeStep}
              onSelectStep={goToStep}
            />
          </div>
          <div className="ar-result-track" aria-hidden="true" />
        </section>

        {/* 분석 결과 저장 · 공유 + 맨 아래 오른쪽 사고 타임라인 바로가기 */}
        <section ref={evidenceRef} className="ar-section ar-report-page ar-evidence-page">
          <div className="ar-evidence-layout">
            <div className="ar-evidence-head">
              <ReportActions content={REPORT_ACTIONS} onShare={share} />
            </div>
          </div>
          {/* 창 오른쪽 아래 구석에 고정, 이 구간에 들어오면 나타남 */}
          <TimelineLink content={REPORT_ACTIONS.timeline} visible={evidenceInView} />
          <ReportNotice />
        </section>

      </main>

      <p className={toast ? "ar-toast is-on" : "ar-toast"} role="status">
        {toast}
      </p>
    </div>
  );
}
