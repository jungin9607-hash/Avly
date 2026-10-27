import { useEffect, useState } from "react";
import { api } from "./client";
import { expireAnalysis, getSession, wasExpired } from "./session";

// 분석 하나를 서버에서 불러온다. 분석 중이면 끝날 때까지 주기적으로 다시 확인한다.
// 이 브라우저에서 만든 분석이 아니면(세션을 모르면) session 이 null 이다.
export default function useAnalysis(analysisId) {
  const session = getSession(analysisId);
  const sessionId = session?.sessionId;
  const [state, setState] = useState({ analysis: null, error: null });
  const [attempt, setAttempt] = useState(0);
  const [, setClock] = useState(0);
  const expiresAt = session?.expiresAt;

  // 화면을 열어 둔 채로 세션이 끝나면 결과를 화면에서도 치운다
  useEffect(() => {
    const remaining = expiresAt ? Date.parse(expiresAt) - Date.now() : 0;
    if (!(remaining > 0)) return undefined;
    const timer = window.setTimeout(() => setClock((n) => n + 1), Math.min(remaining + 500, 2 ** 31 - 1));
    return () => window.clearTimeout(timer);
  }, [expiresAt]);

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
        if (cancelled) return;
        if (error.code === "SESSION_EXPIRED") expireAnalysis(analysisId);   // 세션이 끝나 서버가 결과를 지웠다
        setState({ analysis: null, error });
      }
    };
    tick();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [analysisId, sessionId, attempt]);

  const expired = wasExpired(analysisId);
  return {
    session,
    expired,
    analysis: expired ? null : state.analysis,
    error: state.error,
    loading: Boolean(session) && !state.analysis && !state.error,
    retry: () => setAttempt((n) => n + 1),
  };
}
