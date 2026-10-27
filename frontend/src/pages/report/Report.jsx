import { useEffect, useMemo, useRef, useState } from "react";
import AnalysisGate from "../common/components/AnalysisGate";
import SituationCheckNotice from "../common/components/SituationCheckNotice";
import useNavigationBackdrop from "../common/hooks/useNavigationBackdrop";
import { useNavigate } from "react-router-dom";
import { easyOf, toReportModel } from "../../api/adapters";
import { api } from "../../api/client";
import { expireAnalysis, getSession } from "../../api/session";
import { ROUTES } from "../../routes";
import ReportNotice from "./components/ReportNotice";
import AdjustmentSteps from "./components/AdjustmentSteps";
import ReportHeader from "./components/ReportHeader";
import ReportActions, { TimelineLink } from "./components/ReportActions";
import StatusNotice from "./components/StatusNotice";
import { FACTOR_TITLE, RATIO_LABEL, REPORT_ACTIONS } from "./reportContent";
import { useScrollStep } from "./hooks/useScrollStep";
import "./Report.css";

// 분석 결과 화면. 서버의 분석 결과를 불러와서 상태(확정, 일부만 반영, 기본값만, 확정 불가)에 맞게 보여 준다.
export default function Report({ analysisId }) {
  return (
    <AnalysisGate analysisId={analysisId} active="분석 결과">
      {({ analysis }) => <ReportView analysis={analysis} analysisId={analysisId} />}
    </AnalysisGate>
  );
}

export function ReportView({ analysis, analysisId, similarCases }) {
  const model = useMemo(() => toReportModel(analysis.result, analysisId), [analysis, analysisId]);
  return model.state === "unresolved" ? (
    <UnresolvedView model={model} analysisId={analysisId} similarCases={similarCases} />
  ) : (
    <ResolvedView model={model} analysisId={analysisId} similarCases={similarCases} />
  );
}

/* ---------- 공통 틀: 메뉴, 배경, 너비 측정 ---------- */
function ReportFrame({ children }) {
  const reportRef = useRef(null);
  useNavigationBackdrop(reportRef);

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

  return (
    <div className="ar" ref={reportRef}>
      <main className="ar-main">{children}</main>
    </div>
  );
}

/* ---------- 결과 아래: 상태 안내 · 저장·공유 · 타임라인 바로가기 · 법적 고지 ---------- */
function ActionsSection({ model, analysisId, summaryText, similarCases, children }) {
  const [toast, setToast] = useState("");
  const navigate = useNavigate();
  const sectionRef = useRef(null);
  const session = getSession(analysisId);
  const expiresText = session?.expiresAt
    ? new Date(session.expiresAt).toLocaleTimeString("ko-KR", { hour: "numeric", minute: "2-digit" })
    : null;
  const [inView, setInView] = useState(false);

  // 이 구간이 화면 아래 40% 선 위로 올라오면 "사고 타임라인 바로가기"를 보여 줌 (위로 올라가면 다시 숨김)
  useEffect(() => {
    const io = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), { rootMargin: "0px 0px -40% 0px" });
    io.observe(sectionRef.current);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    if (!toast) return undefined;
    const id = setTimeout(() => setToast(""), 2200);
    return () => clearTimeout(id);
  }, [toast]);

  // 결과 화면의 주소는 이 브라우저에서만 열리므로(세션), 링크 대신 결과 요약 글을 공유한다.
  const share = async () => {
    const data = { title: "에블리 과실 분석 결과", text: summaryText };
    try {
      if (navigator.share) {
        await navigator.share(data);
      } else {
        await navigator.clipboard.writeText(`${data.title}\n${data.text}`);
        setToast("결과 요약을 복사했어요");
      }
    } catch {
      // 사용자가 공유 창을 닫은 경우 등은 조용히 무시
    }
  };

  // 세션이 끝나기를 기다리지 않고 서버의 분석 결과와 영상을 지금 지운다
  const erase = async () => {
    if (!session || !window.confirm(REPORT_ACTIONS.eraseConfirm)) return;
    try {
      await api.deleteAccident(session.accidentId, { sessionId: session.sessionId });
    } catch (error) {
      if (error.code !== "SESSION_EXPIRED" && error.status !== 404) {
        setToast(error.message);
        return;
      }
    }
    expireAnalysis(analysisId);
    navigate(ROUTES.home);
  };

  return (
    <>
      <section ref={sectionRef} className="ar-section ar-report-page ar-evidence-page">
        <div className="ar-evidence-layout">
          {children}
          <SituationCheckNotice check={model.situationCheck} />
          <StatusNotice text={model.state === "partial" ? "" : model.statusText} pending={model.pending} />
          {similarCases}
          <div className="ar-evidence-head">
            <ReportActions content={REPORT_ACTIONS} onShare={share} onSave={() => navigate(ROUTES.document(analysisId))} onErase={erase} expiresText={expiresText} />
          </div>
        </div>
        {/* 창 오른쪽 아래 구석에 고정, 이 구간에 들어오면 나타남 */}
        <TimelineLink content={{ ...REPORT_ACTIONS.timeline, to: ROUTES.timeline(analysisId) }} visible={inView} />
        <ReportNotice />
      </section>
      <p className={toast ? "ar-toast is-on" : "ar-toast"} role="status">
        {toast}
      </p>
    </>
  );
}

/* ---------- 비율을 보여 줄 수 있는 결과 (확정, 일부만 반영, 기본값만) ---------- */
function ResolvedView({ model, analysisId, similarCases }) {
  const resultRef = useRef(null);
  const { step: activeStep, pinned, goToStep } = useScrollStep(resultRef, model.steps.length);
  const shown = model.shown;
  const summaryText = model.final
    ? `AI 예상 과실 비율: 내 차 ${model.final.me}% : 상대 차 ${model.final.other}% (법적 효력이 없는 참고 자료예요)`
    : `${RATIO_LABEL[model.state]}: 내 차 ${shown.me}% : 상대 차 ${shown.other}% (확정한 비율이 아니에요. 법적 효력이 없는 참고 자료예요)`;

  return (
    <ReportFrame>
      {/* 넓은 화면: 안쪽(pin)이 화면에 고정된 채 아래 track 길이만큼 스크롤하면 기본 기준 → 조정 요인 → 최종 순으로 과실 비율이 바뀜 */}
      <section
        ref={resultRef}
        className={`ar-section ar-report-page ar-result-page${pinned ? " is-pinned" : ""}`}
        style={{ "--ar-step-count": model.steps.length }}
      >
        <div className="ar-result-pin">
          <ReportHeader content={model.header} />
          <AdjustmentSteps
            steps={model.steps}
            header={model.factorHeader}
            ratioLabel={RATIO_LABEL[model.state]}
            confirmed={model.state === "final"}
            title={FACTOR_TITLE[model.state]}
            emptyNote={model.appliedCount === 0 && (model.state === "final" || model.state === "partial") ? "적용된 가감요소가 없어서 기본 비율 그대로예요." : ""}
            activeIndex={activeStep}
            onSelectStep={goToStep}
          />
        </div>
        <div className="ar-result-track" aria-hidden="true" />
      </section>
      <ActionsSection model={model} analysisId={analysisId} summaryText={summaryText} similarCases={similarCases} />
    </ReportFrame>
  );
}

/* ---------- 맞는 사고 유형을 못 정한 결과: 비율 없이 상황 설명과 참고 후보만 ---------- */
function UnresolvedView({ model, analysisId, similarCases }) {
  return (
    <ReportFrame>
      <section className="ar-section ar-report-page ar-unresolved-page">
        <ReportHeader content={model.header} />
        {model.candidates.length > 0 && (
          <div className="ar-candidates">
            <h2>가장 가까운 사고 유형 (참고용)</h2>
            <ul>
              {model.candidates.map((c) => (
                <li key={`${c.accident_type_id}-${c.role}`}>
                  <strong>
                    {easyOf(c, "place")} · {easyOf(c, "feature")}
                  </strong>
                  <span>
                    내 차 {easyOf(c, "my_progress")} / 상대 차 {easyOf(c, "other_progress")}
                  </span>
                  <small>이 유형의 기본 비율은 내 차 {c.base_me}% : 상대 차 {c.base_other}%예요. 영상에 적용된다고 확정한 값은 아니에요.</small>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
      <ActionsSection model={model} analysisId={analysisId} similarCases={similarCases} summaryText="사고 유형을 확정하지 못해 과실 비율을 안내하지 않았어요. 법적 효력이 없는 참고 자료예요." />
    </ReportFrame>
  );
}
