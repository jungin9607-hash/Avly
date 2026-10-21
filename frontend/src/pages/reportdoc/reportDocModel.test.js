import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { formatDateTime, toReportDocument } from "./reportDocModel.js";

const fixture = (name) => JSON.parse(readFileSync(new URL(`../../api/fixtures/${name}`, import.meta.url), "utf8"));
const meta = { analysisId: "abcdef12-0000", createdAt: "2026-10-20T14:30:00Z", expiresAt: "2026-10-20T16:30:00Z" };

test("보고서: 확정이면 최종 비율과 산정 과정을 문서로 만든다", () => {
  const doc = toReportDocument(fixture("result_final.json"), meta);
  assert.deepEqual([doc.headline.title, doc.headline.me, doc.headline.other], ["AI 예상 과실 비율", 20, 80]);
  assert.equal(doc.meta.code, "abcdef12");
  assert.equal(doc.steps[0].title, "기본 비율");
  assert.deepEqual([doc.steps[0].me, doc.steps[0].other], [30, 70]);
  assert.match(doc.steps[1].change, /\+10%p/);
  assert.equal(doc.situation.rows.find(([k]) => k === "사고 유형")[1].length > 0, true);
  assert.ok(doc.situation.official.includes("차로변경(진로변경)"), "과실표 원래 표기를 함께 적는다");
  assert.ok(doc.cases.length > 0 && doc.cases.length <= 3);
  assert.ok(doc.sources.includes("손해보험협회 과실비율 인정기준(2023.06)"));
});

test("보고서: 사용자가 '아니요'로 답한 항목은 한 줄로 모으고 누구 이야기인지 붙인다", () => {
  const result = fixture("result_final.json");
  const doc = toReportDocument(result, meta);
  const noCount = result.adjustments.not_applied.filter((p) => p.reason === "해당 요소 없음으로 확인").length;
  assert.equal(doc.answeredNo.length, noCount);
  assert.ok(doc.answeredNo.every((t) => /^(내 차|상대 차): /.test(t)));
  assert.equal(doc.notApplied.length, result.adjustments.not_applied.length - noCount);
});

test("보고서: 확정하지 못한 결과는 있는 값만 말하고 비율을 지어내지 않는다", () => {
  const unresolved = toReportDocument(fixture("result_unresolved.json"), meta);
  assert.equal(unresolved.headline.me, null);
  assert.equal(unresolved.steps.length, 0);
  assert.match(unresolved.headline.note, /맞는 사고 유형을 찾지 못해/);
  const partial = toReportDocument(fixture("result_partial.json"), meta);
  assert.equal(partial.headline.title, "확인한 요소만 반영한 예상 비율");
  assert.ok(partial.headline.me != null);
  const base = toReportDocument(fixture("result_base_only.json"), meta);
  assert.match(base.headline.title, /기본 비율/);
});

test("보고서: 법령 풀이가 없으면 안내 문장을 쓰고, 날짜는 읽기 쉽게 바꾼다", () => {
  const doc = toReportDocument(fixture("result_final.json"), meta);
  assert.ok(doc.laws.some((l) => /준비하고 있어요/.test(l.easy)));
  assert.match(formatDateTime("2026-10-20T14:30:00Z"), /2026년 10월/);
  assert.equal(formatDateTime(null), "");
  assert.equal(toReportDocument(fixture("result_final.json"), {}).meta.createdAt, "");
});

test("보고서: 사고 흐름이 있으면 타임라인 절에 단계로 들어간다", () => {
  const result = { ...fixture("result_final.json"), timeline: [{ kind: "사고 흐름", stage: "접근", actor: null, start_sec: 0, end_sec: 2, description: "내 차가 직진해요.", certainty: "관찰" }], timeline_note: "상대 차는 처음 보인 뒤 약 2.0초 뒤에 접촉이 의심되는 장면이 나와요." };
  const doc = toReportDocument(result, meta);
  assert.deepEqual(doc.timeline.rows.map((r) => r.label), ["접근"]);
  assert.match(doc.timeline.note, /약 2\.0초/);
});

test("보고서: 맨 위 한 줄 설명은 확정된 사고 유형으로 만들고, 유형이 없으면 서버 요약을 쓴다", () => {
  const result = fixture("result_final.json");
  assert.match(toReportDocument(result, meta).headline.oneLine, /사고예요\. 내 차는 .+, 상대 차는 .+ 상황이에요\./);
  const unresolved = { ...fixture("result_unresolved.json"), summary: "AI가 본 장면 요약" };
  assert.equal(toReportDocument(unresolved, meta).headline.oneLine, unresolved.accident_type ? toReportDocument(unresolved, meta).headline.oneLine : "AI가 본 장면 요약");
});
