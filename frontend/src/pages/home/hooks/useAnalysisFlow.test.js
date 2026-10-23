// 실행: node --test src/pages/home/useAnalysisFlow.test.js
import assert from "node:assert/strict";
import { test } from "node:test";
import { applyAnalysis, initialState, reducer } from "./useAnalysisFlow.js";

const analyzing = { phase: "analyzing", stage: null, analysisId: "a1", accidentId: "c1", sessionId: "s1" };

test("분석 중에는 진행 단계만 바뀐다", () => {
  const next = reducer(analyzing, { type: "polled", analysis: { status: "processing", stage: { id: "overview" } } });
  assert.deepEqual([next.phase, next.stage], ["analyzing", "overview"]);
  const kept = reducer(next, { type: "polled", analysis: { status: "queued", stage: null } });
  assert.equal(kept.stage, "overview", "단계 정보가 잠깐 비어도 이전 단계를 유지한다");
});

test("분석이 끝나면 사용자 확인 단계로 간다", () => {
  const situation = { candidates: [], default_index: null };
  const next = reducer(analyzing, { type: "polled", analysis: { status: "awaiting_confirmation", situation } });
  assert.equal(next.phase, "confirming");
  assert.equal(next.situation, situation);
});

test("확인 단계에서 같은 응답을 또 받아도 사용자의 진행을 되돌리지 않는다", () => {
  const confirming = { ...analyzing, phase: "confirming", situation: {} };
  assert.equal(reducer(confirming, { type: "polled", analysis: { status: "awaiting_confirmation", situation: { x: 1 } } }), confirming);
  const adjusting = { ...confirming, phase: "adjusting", option: {}, questions: [] };
  assert.equal(reducer(adjusting, { type: "polled", analysis: { status: "awaiting_confirmation", situation: {} } }), adjusting);
});

test("결과 계산 중에 아직 확인 대기 응답이 와도 계산 중으로 남는다", () => {
  const finalizing = reducer({ ...analyzing, phase: "confirming" }, { type: "finalizing" });
  assert.deepEqual([finalizing.phase, finalizing.stage], ["finalizing", "finalize"]);
  assert.equal(reducer(finalizing, { type: "polled", analysis: { status: "awaiting_confirmation" } }).phase, "finalizing");
  assert.equal(reducer(finalizing, { type: "polled", analysis: { status: "processing", stage: { id: "finalize" } } }).phase, "finalizing");
  assert.equal(reducer(finalizing, { type: "polled", analysis: { status: "completed" } }).phase, "done");
});

test("지원하지 않는 사고와 실패는 이유를 담는다", () => {
  const unsupported = reducer(analyzing, { type: "polled", analysis: { status: "unsupported", unsupported_reason: "차대보행자 사고는 지원하지 않습니다." } });
  assert.deepEqual([unsupported.phase, unsupported.unsupportedReason], ["unsupported", "차대보행자 사고는 지원하지 않습니다."]);
  const failed = reducer(analyzing, { type: "polled", analysis: { status: "failed", error: { code: "VIDEO_TOO_LONG", message: "너무 깁니다" } } });
  assert.deepEqual([failed.phase, failed.error.code], ["failed", "VIDEO_TOO_LONG"]);
});

test("요청 오류는 코드와 메시지로 정리된다", () => {
  const next = reducer(analyzing, { type: "failed", error: { code: "NETWORK_ERROR", message: "연결 실패" } });
  assert.deepEqual(next.error, { code: "NETWORK_ERROR", message: "연결 실패" });
  assert.equal(reducer(analyzing, { type: "failed", error: new Error("x") }).error.code, "UNKNOWN");
});

test("업로드 진행률은 업로드 중일 때만 반영한다", () => {
  const up = reducer(initialState, { type: "uploading" });
  assert.equal(reducer(up, { type: "progress", progress: 0.4 }).progress, 0.4);
  assert.equal(reducer(analyzing, { type: "progress", progress: 0.4 }), analyzing);
});

test("가감 질문 단계에서 이전으로 돌아갈 수 있다", () => {
  const adjusting = { ...analyzing, phase: "adjusting", option: { accident_type_id: 11 }, questions: [1] };
  assert.equal(reducer(adjusting, { type: "back" }).phase, "confirming");
  assert.equal(reducer(analyzing, { type: "back" }), analyzing);
});

test("처음으로 돌아가기", () => {
  assert.equal(reducer({ ...analyzing, phase: "failed" }, { type: "reset" }), initialState);
});

test("applyAnalysis 는 모르는 상태에서도 오류 없이 현재 상태를 돌려준다", () => {
  assert.deepEqual(applyAnalysis(analyzing, { status: "something_new", stage: null }), { ...analyzing, stage: null });
});

test("서버가 취소했다고 알려 주면(예: 이어서 보기로 들어온 경우) 실패 상태가 되고 오류 코드가 CANCELLED 로 남는다", () => {
  const next = applyAnalysis(analyzing, { status: "failed", error: { code: "CANCELLED", message: "분석을 취소했어요." } });
  assert.equal(next.phase, "failed");
  assert.equal(next.error.code, "CANCELLED");
  // 화면에서 취소하면 같은 모양의 실패 상태가 된다
  const local = reducer(analyzing, { type: "failed", error: { code: "CANCELLED", message: "분석을 취소했어요." } });
  assert.deepEqual([local.phase, local.error.code], ["failed", "CANCELLED"]);
});

test("가감요소 질문 화면은 검수 전이라 묻지 않은 항목 수를 가진다", () => {
  const confirming = { ...analyzing, phase: "confirming" };
  const option = { accident_type_id: 11, role: "A" };
  assert.equal(reducer(confirming, { type: "adjusting", option, questions: [], heldBack: 4 }).heldBack, 4);
  assert.equal(reducer(confirming, { type: "adjusting", option, questions: [] }).heldBack, 0);
});
