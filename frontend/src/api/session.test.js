import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";
import { expireAnalysis, forgetAnalysis, getSession, lastAnalysisId, rememberAnalysis, wasExpired } from "./session.js";

// 브라우저의 localStorage 를 흉내 낸다
beforeEach(() => {
  const store = new Map();
  globalThis.window = {
    localStorage: { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) },
  };
});

const inHours = (h) => new Date(Date.now() + h * 3600 * 1000).toISOString();

test("세션이 끝나기 전에는 접근 정보를 돌려준다", () => {
  rememberAnalysis("a1", "acc1", "sid1", inHours(2));
  assert.deepEqual([getSession("a1").sessionId, lastAnalysisId(), wasExpired("a1")], ["sid1", "a1", false]);
});

test("세션이 끝난 분석은 접근 정보를 지우고 끝났다는 표시만 남긴다", () => {
  rememberAnalysis("a1", "acc1", "sid1", inHours(-1));
  assert.equal(getSession("a1"), null);
  assert.equal(lastAnalysisId(), null);
  assert.equal(wasExpired("a1"), true);
  assert.equal(window.localStorage.getItem("avly.sessions").includes("sid1"), false);   // 세션 값이 브라우저에 남지 않는다
});

test("서버가 끝났다고 알려 주면 바로 지운다", () => {
  rememberAnalysis("a1", "acc1", "sid1", inHours(2));
  expireAnalysis("a1");
  assert.deepEqual([getSession("a1"), lastAnalysisId(), wasExpired("a1")], [null, null, true]);
});

test("모르는 분석은 끝난 것이 아니라 없는 것이다", () => {
  assert.deepEqual([getSession("none"), wasExpired("none")], [null, false]);
});

test("만료 시각을 모르는 이전 기록도 그대로 쓴다", () => {
  rememberAnalysis("a1", "acc1", "sid1");
  assert.equal(getSession("a1").sessionId, "sid1");
});

test("저장소 읽기와 쓰기가 차단되어도 현재 탭에서 결과에 접근하고 삭제할 수 있다", () => {
  window.localStorage = {
    getItem() { throw new Error("blocked"); },
    setItem() { throw new Error("blocked"); },
  };
  rememberAnalysis("a1", "acc1", "sid1", inHours(2));
  assert.equal(getSession("a1").sessionId, "sid1");
  assert.equal(lastAnalysisId(), "a1");
  expireAnalysis("a1");
  assert.equal(getSession("a1"), null);
  assert.equal(wasExpired("a1"), true);
  assert.equal(lastAnalysisId(), null);
  forgetAnalysis("a1");
  assert.equal(wasExpired("a1"), false);
});

test("쓰기만 차단된 저장소도 메모리의 최신 값과 만료 상태를 사용한다", () => {
  rememberAnalysis("a1", "acc1", "old", inHours(2));
  window.localStorage.setItem = () => { throw new Error("quota"); };
  rememberAnalysis("a1", "acc1", "new", inHours(2));
  assert.equal(getSession("a1").sessionId, "new");
  expireAnalysis("a1");
  assert.equal(getSession("a1"), null);
  assert.equal(lastAnalysisId(), null);
  rememberAnalysis("a2", "acc2", "sid2", inHours(-1));
  assert.equal(getSession("a2"), null);
  assert.equal(wasExpired("a2"), true);
});
