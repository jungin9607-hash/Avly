import { useCallback, useEffect, useReducer, useRef } from "react";
import { api } from "../../../api/client.js";
import { CONSENT_VERSION } from "../../../api/config.js";
import { expireAnalysis, forgetAnalysis, getSession, rememberAnalysis } from "../../../api/session.js";

// 영상 올리기 → 분석 → (사용자 확인) → 가감 질문 → 결과 계산까지 한 줄로 이어지는 흐름.
// 화면은 phase 만 보고 어떤 팝업을 띄울지 정한다.
//   idle        아무것도 시작하지 않음
//   uploading   사고를 만들고 영상을 올리는 중 (progress 0~1)
//   analyzing   서버가 비식별화와 분석 중 (stage)
//   confirming  사용자가 AI 가 파악한 사고 상황을 확인할 차례 (situation, catalog)
//   adjusting   사용자가 가감요소 질문에 답할 차례 (option, questions)
//   finalizing  서버가 결과를 계산하는 중
//   done        결과가 나옴 (analysisId 로 이동)
//   unsupported 차대차가 아닌 사고 (unsupportedReason)
//   failed      실패 (error)
const POLL_MS = 1200;

export const initialState = { phase: "idle" };

// 사용자가 나갔다가 돌아와서 이어서 확인하는 경우(?resume=분석번호): 이 브라우저가 아는 분석이면 분석 중 상태에서 시작한다.
export function initFrom(resumeId) {
  const session = resumeId ? getSession(resumeId) : null;
  return session ? { phase: "analyzing", stage: null, analysisId: resumeId, accidentId: session.accidentId, sessionId: session.sessionId } : initialState;
}

// 이 상태에서 서버 응답(analysis)을 받으면 어떤 상태가 되는지
export function applyAnalysis(state, analysis) {
  switch (analysis.status) {
    case "completed":
      return { ...state, phase: "done", stage: null };
    case "unsupported":
      return { ...state, phase: "unsupported", unsupportedReason: analysis.unsupported_reason };
    case "failed":
      return { ...state, phase: "failed", error: analysis.error };
    case "awaiting_confirmation":
      // 분석이 끝났다. 사용자가 이미 다음 단계에 있다면 되돌리지 않는다.
      return state.phase === "analyzing" ? { ...state, phase: "confirming", stage: null, situation: analysis.situation } : state;
    default:
      return { ...state, stage: analysis.stage?.id ?? state.stage ?? null };
  }
}

export function reducer(state, action) {
  switch (action.type) {
    case "reset":
      return initialState;
    case "uploading":
      return { phase: "uploading", progress: 0 };
    case "progress":
      return state.phase === "uploading" ? { ...state, progress: action.progress } : state;
    case "analyzing":
      return { phase: "analyzing", stage: null, analysisId: action.analysisId, accidentId: action.accidentId, sessionId: action.sessionId };
    case "polled":
      return applyAnalysis(state, action.analysis);
    case "catalog":
      return { ...state, catalog: action.items };
    case "adjusting":
      return { ...state, phase: "adjusting", option: action.option, questions: action.questions, heldBack: action.heldBack ?? 0 };
    case "back":
      return state.phase === "adjusting" ? { ...state, phase: "confirming" } : state;
    case "finalizing":
      return { ...state, phase: "finalizing", stage: "finalize" };
    case "failed":
      return { ...state, phase: "failed", error: { code: action.error.code ?? "UNKNOWN", message: action.error.message } };
    default:
      return state;
  }
}

const titleFrom = (file) => (file.name.replace(/\.[^.]+$/, "").trim() || "블랙박스 영상").slice(0, 200);

export default function useAnalysisFlow(resumeId) {
  const [state, dispatch] = useReducer(reducer, resumeId, initFrom);
  const controller = useRef(null);

  const start = useCallback(async (file, retention, place) => {
    controller.current?.abort();
    controller.current = new AbortController();
    const signal = controller.current.signal;
    dispatch({ type: "uploading" });
    try {
      const accident = await api.createAccident(titleFrom(file), { version: CONSENT_VERSION, analysis: true, retention }, { signal });
      const opts = { sessionId: accident.session_id, signal };
      await api.uploadVideo(accident.id, file, { ...opts, onProgress: (progress) => dispatch({ type: "progress", progress }) });
      const started = await api.startAnalysis(accident.id, place, opts);
      rememberAnalysis(started.analysis_id, accident.id, accident.session_id, accident.expires_at);
      dispatch({ type: "analyzing", analysisId: started.analysis_id, accidentId: accident.id, sessionId: accident.session_id });
    } catch (error) {
      if (error.name !== "AbortError") dispatch({ type: "failed", error });
    }
  }, []);

  // 서버가 알려 준 오류로 실패 상태가 된다. 세션이 끝났다는 오류면 이 브라우저에 남은 접근 정보도 지운다.
  const fail = useCallback((error, id) => {
    if (error.code === "SESSION_EXPIRED" && id) expireAnalysis(id);
    dispatch({ type: "failed", error });
  }, []);

  // 서버가 일하는 동안 상태를 주기적으로 확인한다
  const { phase, analysisId, sessionId } = state;
  useEffect(() => {
    if (phase !== "analyzing" && phase !== "finalizing") return undefined;
    let cancelled = false;
    let timer = 0;
    const tick = async () => {
      try {
        const analysis = await api.getAnalysis(analysisId, { sessionId });
        if (cancelled) return;
        dispatch({ type: "polled", analysis });
        if (["queued", "processing"].includes(analysis.status) || (analysis.status === "awaiting_confirmation" && phase === "finalizing")) {
          timer = window.setTimeout(tick, POLL_MS);
        }
      } catch (error) {
        if (!cancelled) fail(error, analysisId);
      }
    };
    tick();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [phase, analysisId, sessionId, fail]);

  // 사고 상황을 확인하는 화면에 들어오면 과실표 선택지를 한 번 받아 둔다
  const hasCatalog = Boolean(state.catalog);
  useEffect(() => {
    if (phase !== "confirming" || hasCatalog) return undefined;
    let cancelled = false;
    api.catalog().then(
      (body) => !cancelled && dispatch({ type: "catalog", items: body.items }),
      (error) => !cancelled && dispatch({ type: "failed", error }),
    );
    return () => {
      cancelled = true;
    };
  }, [phase, hasCatalog]);

  const confirm = useCallback(async (option, answers) => {
    dispatch({ type: "finalizing" });
    try {
      await api.confirm(
        analysisId,
        {
          accident_type_id: option ? option.accident_type_id : null,
          role: option ? option.role : null,
          answers: Object.entries(answers).map(([key, answer]) => ({ key, answer })),
        },
        { sessionId },
      );
    } catch (error) {
      fail(error, analysisId);
    }
  }, [analysisId, sessionId, fail]);

  // 사용자가 고른 사고 유형의 가감요소 질문을 받아 오고, 없으면 바로 결과 계산으로 넘어간다
  const choose = useCallback(async (option) => {
    if (!option) return confirm(null, {});
    try {
      const body = await api.adjustmentQuestions(analysisId, option.accident_type_id, option.role, { sessionId });
      if (body.questions.length === 0) return confirm(option, {});
      dispatch({ type: "adjusting", option, questions: body.questions, heldBack: body.held_back ?? 0 });
    } catch (error) {
      fail(error, analysisId);
    }
    return undefined;
  }, [analysisId, sessionId, confirm, fail]);

  // 분석 중인 분석을 취소한다. 서버가 취소를 받아들이면 "취소했어요" 안내로 넘어간다.
  // 그사이 분석이 끝났거나 사용자 확인 단계가 됐다면(409) 취소하지 못한 것이므로 상태 확인이 알아서 다음 화면으로 넘긴다.
  const cancel = useCallback(async () => {
    try {
      await api.cancelAnalysis(analysisId, { sessionId });
      forgetAnalysis(analysisId); // 취소한 분석은 최근 분석으로 기억하지 않는다 (상단 메뉴가 "블랙박스 영상을 먼저 올려 주세요"로 연결되도록)
      dispatch({ type: "failed", error: { code: "CANCELLED", message: "분석을 취소했어요." } });
    } catch (error) {
      if (error.code !== "ANALYSIS_NOT_CANCELLABLE") fail(error, analysisId);
    }
  }, [analysisId, sessionId, fail]);

  const reset = useCallback(() => {
    controller.current?.abort();
    dispatch({ type: "reset" });
  }, []);

  return { state, start, choose, confirm, cancel, back: () => dispatch({ type: "back" }), reset };
}
