// 로그인이 없으므로 사고를 만들 때 서버가 준 session_id 를 브라우저에 기억해 두고 요청마다 보낸다.
// 저장소를 쓸 수 없는 환경(사생활 보호 창 등)에서도 화면이 동작하도록 모든 접근을 감싼다.
// 분석 결과는 세션이 끝나면 서버에서 지워진다. 끝난 분석은 접근 정보를 지우고 "끝났다"는 표시만 남겨서, 다시 열었을 때 "삭제됐어요"라고 알려 준다.
const SESSIONS = "avly.sessions"; // { [analysisId]: { accidentId, sessionId, expiresAt } | { expired: true } }
const LAST = "avly.lastAnalysis";
// 저장소 읽기/쓰기가 차단되면 현재 탭의 메모리에 접근 정보를 유지한다.
const memoryByWindow = new WeakMap();

function memory() {
  if (!memoryByWindow.has(window)) memoryByWindow.set(window, { values: new Map(), pending: new Set() });
  return memoryByWindow.get(window);
}

function read(key) {
  const cache = memory();
  if (cache.pending.has(key)) return cache.values.get(key) ?? null;
  try {
    const value = JSON.parse(window.localStorage.getItem(key) ?? "null");
    cache.values.set(key, value);
    return value;
  } catch {
    return cache.values.get(key) ?? null;
  }
}

function write(key, value) {
  const cache = memory();
  cache.values.set(key, value);
  cache.pending.add(key);
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
    cache.pending.delete(key);
  } catch {
    // 저장하지 못해도 이번 화면에서는 계속 쓸 수 있다
  }
}

export function rememberAnalysis(analysisId, accidentId, sessionId, expiresAt = null) {
  write(SESSIONS, { ...(read(SESSIONS) ?? {}), [analysisId]: { accidentId, sessionId, expiresAt } });
  write(LAST, analysisId);
}

// 세션이 끝난 분석의 접근 정보를 지운다 (서버가 SESSION_EXPIRED 를 알려 줬거나, 결과를 직접 지웠을 때)
export function expireAnalysis(analysisId) {
  write(SESSIONS, { ...(read(SESSIONS) ?? {}), [analysisId]: { expired: true } });
  if (read(LAST) === analysisId) write(LAST, null);
}

// 이 브라우저가 알고 있고 아직 세션이 끝나지 않은 분석만 돌려준다. 끝난 분석이면 null.
export function getSession(analysisId) {
  const entry = (read(SESSIONS) ?? {})[analysisId] ?? null;
  if (!entry || entry.expired) return null;
  if (entry.expiresAt && Date.parse(entry.expiresAt) <= Date.now()) {
    expireAnalysis(analysisId);
    return null;
  }
  return entry;
}

export function wasExpired(analysisId) {
  return Boolean((read(SESSIONS) ?? {})[analysisId]?.expired);
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
