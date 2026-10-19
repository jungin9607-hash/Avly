import { useEffect, useState } from "react";
import { api } from "./client";
import { getSession } from "./session";

// 분석 하나를 서버에서 불러온다. 분석 중이면 끝날 때까지 주기적으로 다시 확인한다.
// 이 브라우저에서 만든 분석이 아니면(세션을 모르면) session 이 null 이다.
export default function useAnalysis(analysisId) {
  const session = getSession(analysisId);
  const sessionId = session?.sessionId;
  const [state, setState] = useState({ analysis: null, error: null });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!sessionId) return undefined;
    let cancelled = false;
    let timer = 0;
    const tick = async () => {
      try {
        const analysis = await api.getAnalysis(analysisId, { sessionId });
        if (cancelled) return;
        setState({ analysis, error: null });
        if (analysis.status === "queued" || analysis.status === "processing") timer = window.setTimeout(tick, 1500);
      } catch (error) {
        if (!cancelled) setState({ analysis: null, error });
      }
    };
    tick();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [analysisId, sessionId, attempt]);

  return {
    session,
    analysis: state.analysis,
    error: state.error,
    loading: Boolean(session) && !state.analysis && !state.error,
    retry: () => setAttempt((n) => n + 1),
  };
}
