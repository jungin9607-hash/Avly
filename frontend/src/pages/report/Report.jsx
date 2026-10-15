import { useEffect, useRef, useState } from "react";
import TopNav from "../../components/common/TopNav";
import useNavigationBackdrop from "../../components/common/useNavigationBackdrop";
import ReportNotice from "./ReportNotice";
import AdjustmentSteps from "./AdjustmentSteps";
import ReportHeader from "./ReportHeader";
import EvidenceCard from "./EvidenceCard";
import ReportActions from "./ReportActions";
import SectionHeader, { ShieldSearchIcon } from "./SectionHeader";
import {
  REPORT_HEADER,
  FACTOR_HEADER,
  STEPS,
  EVIDENCE_HEADER,
  EVIDENCE,
  REPORT_ACTIONS,
} from "./reportContent";
import { useScrollStep } from "./useScrollStep";
import "./Report.css";

export default function Report() {
  const [toast, setToast] = useState("");
  const reportRef = useRef(null);
  useNavigationBackdrop(reportRef);
  const resultRef = useRef(null);
  const { step: activeStep, pinned } = useScrollStep(resultRef, STEPS.length);

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

      {/* 배경 워터마크: 아주 옅은 "Avly" 글자 */}
      <span className="ar-wordmark" aria-hidden="true">Avly</span>

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
            <AdjustmentSteps steps={STEPS} header={FACTOR_HEADER} activeIndex={activeStep} />
          </div>
          <div className="ar-result-track" aria-hidden="true" />
        </section>

        {/* 영상 증거: 왼쪽 세로 카드 목록 | 오른쪽 저장·공유·유사 판례 패널 */}
        <section className="ar-section ar-report-page ar-evidence-page">
          {/* 영상 증거 구간: 가감요소 구간과 확실히 나뉘도록 큰 박스로 감쌈 */}
          <div className="ar-panel ar-evidence-layout">
            <div className="ar-evidence-col">
              <SectionHeader icon={<ShieldSearchIcon />} title={EVIDENCE_HEADER.title} desc={EVIDENCE_HEADER.desc} />
              <div className="ar-evidence">
                {EVIDENCE.map((item, i) => (
                  <Reveal key={item.title} className="ar-ev" delay={i * 80}>
                    {() => <EvidenceCard item={item} index={i} />}
                  </Reveal>
                ))}
              </div>
            </div>
            <ReportActions content={REPORT_ACTIONS} onShare={share} />
          </div>
          <ReportNotice />
        </section>

      </main>

      <p className={toast ? "ar-toast is-on" : "ar-toast"} role="status">
        {toast}
      </p>
    </div>
  );
}

/* ---------- 작은 부품 ---------- */

function Reveal({ className, delay = 0, children }) {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setInView(true);
          io.disconnect();
        }
      },
      { threshold: 0.25 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <article
      ref={ref}
      className={`${className} ar-reveal${inView ? " is-in" : ""}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children(inView)}
    </article>
  );
}
