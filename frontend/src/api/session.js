// 로그인이 없으므로 사고를 만들 때 서버가 준 session_id 를 브라우저에 기억해 두고 요청마다 보낸다.
// 저장소를 쓸 수 없는 환경(사생활 보호 창 등)에서도 화면이 동작하도록 모든 접근을 감싼다.
const SESSIONS = "avly.sessions"; // { [analysisId]: { accidentId, sessionId } }
const LAST = "avly.lastAnalysis";

function read(key) {
  try {
    return JSON.parse(window.localStorage.getItem(key) ?? "null");
  } catch {
    return null;
  }
}

function write(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // 저장하지 못해도 이번 화면에서는 계속 쓸 수 있다
  }
}

export function rememberAnalysis(analysisId, accidentId, sessionId) {
  write(SESSIONS, { ...(read(SESSIONS) ?? {}), [analysisId]: { accidentId, sessionId } });
  write(LAST, analysisId);
}

export function getSession(analysisId) {
  return (read(SESSIONS) ?? {})[analysisId] ?? null;
}

export function lastAnalysisId() {
  const id = read(LAST);
  return id && getSession(id) ? id : null;
}

export function forgetAnalysis(analysisId) {
  const { [analysisId]: removed, ...rest } = read(SESSIONS) ?? {};
  void removed;
  write(SESSIONS, rest);
  if (read(LAST) === analysisId) write(LAST, null);
}
