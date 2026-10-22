// 실행: node --test src/api/adapters.test.js   (Node 내장 테스트 도구. 추가 설치가 필요 없다)
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  autoFill, cascade, commonSelection, easySituation, myAccidentPoints, normalizeSelection, resolveOption, selectionFrom, stageIndex, toCaseCards, toMoments, toReportModel, toSteps,
} from "./adapters.js";

const fixture = (name) => JSON.parse(readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8"));
const catalog = fixture("catalog.json");
const items = catalog.items;

test("과실표 선택지는 네 항목으로 유형 하나가 정해진다", () => {
  const keys = items.map((i) => [i.place, i.feature, i.my_progress, i.other_progress].join("|"));
  assert.equal(new Set(keys).size, keys.length);
  assert.equal(items.length, catalog.count);
});

test("앞 항목을 고르면 뒤 항목의 보기가 좁혀진다", () => {
  const place = "직선 도로";
  const afterPlace = cascade(items, { place, feature: "", my_progress: "", other_progress: "" });
  assert.ok(afterPlace.feature.length > 0);
  for (const feature of afterPlace.feature) assert.ok(items.some((i) => i.place === place && i.feature === feature));
  const everyFeature = new Set(items.map((i) => i.feature));
  assert.ok(afterPlace.feature.length < everyFeature.size, "장소를 고르면 사고 유형이 줄어든다");
  const feature = afterPlace.feature[0];
  const afterFeature = cascade(items, { place, feature, my_progress: "", other_progress: "" });
  for (const progress of afterFeature.my_progress) assert.ok(items.some((i) => i.place === place && i.feature === feature && i.my_progress === progress));
});

test("장소를 고르기 전에는 사고 유형 보기가 없다", () => {
  const options = cascade(items, { place: "", feature: "", my_progress: "", other_progress: "" });
  assert.equal(options.feature.length, 0);
  assert.equal(options.my_progress.length, 0);
});

test("네 항목이 모두 정해지면 유형 번호와 역할을 돌려준다", () => {
  const picked = items.find((i) => i.accident_type_id === 11 && i.role === "A");
  const found = resolveOption(items, selectionFrom(picked));
  assert.equal(found.accident_type_id, 11);
  assert.equal(found.role, "A");
  assert.equal(resolveOption(items, { ...selectionFrom(picked), other_progress: "" }), null);
});

test("모든 선택지는 자기 네 항목으로 다시 찾아진다", () => {
  for (const item of items) {
    const found = resolveOption(items, selectionFrom(item));
    assert.equal(found.accident_type_id, item.accident_type_id);
    assert.equal(found.role, item.role);
  }
});

test("앞 항목을 바꾸면 이제 맞지 않는 뒤 항목의 선택은 지워진다", () => {
  const picked = items.find((i) => i.accident_type_id === 11 && i.role === "A");
  const selection = selectionFrom(picked);
  const other = items.find((i) => i.place !== picked.place);
  const next = normalizeSelection(items, { ...selection, place: other.place });
  assert.equal(next.place, other.place);
  assert.equal(next.feature, "");
  assert.equal(next.my_progress, "");
  assert.equal(next.other_progress, "");
  // 같은 장소 안에서 바꾸면 맞는 항목은 유지된다
  assert.deepEqual(normalizeSelection(items, selection), selection);
});

test("진행 단계 위치", () => {
  assert.equal(stageIndex("plate_masking"), 0);
  assert.equal(stageIndex("case_matching"), 3);
  assert.equal(stageIndex("finalize"), -1);
  assert.equal(stageIndex(null), -1);
});

test("확정 결과는 단계 카드로 바뀐다", () => {
  const result = fixture("result_final.json");
  const model = toReportModel(result, "3f2a1c9e-0000-0000-0000-000000000000");
  assert.equal(model.state, "final");
  assert.equal(model.steps.length, 2);
  assert.deepEqual(model.steps[0].ratio, [30, 70]);
  assert.equal(model.steps[0].tag, "출발점");
  assert.deepEqual(model.steps[1].ratio, [20, 80]);
  assert.equal(model.steps[1].tag, "상대 차 과실 +10%p");
  assert.deepEqual(model.final, { me: 20, other: 80 });
  assert.ok(model.steps[0].legal.length > 0, "법적 근거는 첫 단계에 붙는다");
  assert.deepEqual(model.steps[1].legal, []);
  assert.equal(model.header.keywords.at(-1), "식별 코드 3f2a1c9e");
  assert.match(model.factorHeader.desc, /1가지 가감요소/);
});

test("확인하지 못한 요소가 있으면 최종 비율 없이 지금까지 반영한 값만 보여 준다", () => {
  const model = toReportModel(fixture("result_partial.json"), "a");
  assert.equal(model.state, "partial");
  assert.equal(model.final, null);
  assert.deepEqual([model.shown.me, model.shown.other], [20, 80]);
  assert.ok(model.pending.length > 0);
  assert.match(model.factorHeader.desc, /확인한 가감요소만/);
});

test("확인하지 못한 요소만 있고 적용된 가감요소가 없으면 기본 비율 그대로라고 알려 준다", () => {
  const result = structuredClone(fixture("result_partial.json"));
  result.adjustments.applied = [];
  result.steps = result.steps.slice(0, 1);
  const model = toReportModel(result, "a");
  assert.equal(model.appliedCount, 0);
  assert.match(model.factorHeader.desc, /적용된 가감요소가 없어서 기본 비율 그대로/);
  assert.equal(toReportModel(fixture("result_partial.json"), "a").appliedCount, 1);
});

test("가감요소가 없는 유형은 기본 비율만 보여 준다", () => {
  const model = toReportModel(fixture("result_base_only.json"), "a");
  assert.equal(model.state, "base_only");
  assert.equal(model.steps.length, 1);
  assert.equal(model.final, null);
  assert.match(model.factorHeader.desc, /기본 비율만/);
});

test("유형을 못 정한 결과에는 비율이 없다", () => {
  const model = toReportModel(fixture("result_unresolved.json"), "a");
  assert.equal(model.state, "unresolved");
  assert.deepEqual([model.steps, model.shown, model.final], [[], null, null]);
  assert.ok(model.candidates.length > 0);
  assert.equal(model.header.keywords.length, 1);
});

test("법조문 풀이가 없으면 안내 문구를 대신 보여 준다", () => {
  const result = fixture("result_final.json");
  const steps = toSteps({ ...result, laws: [{ label: "도로교통법 제14조", name: null, easy: null }] });
  assert.equal(steps[0].legal[0].name, "도로교통법 제14조");
  assert.match(steps[0].legal[0].text, /준비하고 있어요/);
});

test("타임라인: 접촉이 확실하면 충돌 시점을 기준으로 말한다", () => {
  const result = fixture("result_final.json");
  assert.equal(result.impact.confirmed, true);
  const moments = toMoments(result);
  const times = moments.map((m) => m.time);
  assert.deepEqual(times, [...times].sort((a, b) => a - b));
  const contact = moments.find((m) => m.tone === "impact");
  assert.equal(contact.label, "충돌 시점");
  assert.ok(moments.some((m) => /^충돌 [\d.]+초 (전|후)$/.test(m.label)));
  for (const m of moments) assert.equal(m.hud, "CAM_FRONT");
});

test("타임라인: 시간축 위치는 단계 수만큼 고르게 나뉜다", () => {
  const event = (kind, start) => ({ kind, actor: "me", start_sec: start, end_sec: start + 0.2, description: "d", certainty: "c" });
  const moments = toMoments({ timeline: [event("A 움직임", 1), event("B 확인 구간", 3), event("접촉 근거 구간", 5), event("A 움직임", 8)], impact: {} });
  const expected = [0, 100 / 3, 200 / 3, 100];
  assert.equal(moments.length, 4);
  moments.forEach((m, i) => assert.ok(Math.abs(m.position - expected[i]) < 1e-9, `${i}번째 위치 ${m.position}`));
  assert.deepEqual(toMoments({ timeline: [event("A 움직임", 1)], impact: {} }).map((m) => m.position), [0]);
});

test("타임라인: 끊겨서 이어지는 같은 상태의 내 차 움직임은 하나로 합친다", () => {
  const move = (start, end, certainty = "이동 추정") => ({ kind: "A 움직임", actor: "me", start_sec: start, end_sec: end, certainty });
  const [only] = toMoments({ timeline: [move(2.33, 5.73), move(5.8, 6.4)], impact: {} });
  assert.equal(toMoments({ timeline: [move(2.33, 5.73), move(5.8, 6.4)], impact: {} }).length, 1);
  assert.equal(only.endTime, 6.4);
  // 상태가 다르거나 간격이 넓으면 따로 둔다
  assert.equal(toMoments({ timeline: [move(1, 3), move(3.1, 6, "정지 추정")], impact: {} }).length, 2);
  assert.equal(toMoments({ timeline: [move(1, 3), move(5, 6)], impact: {} }).length, 2);
});

test("타임라인: 시작 시각이 비슷한 관찰은 한 단계로 묶고 같은 장면이 반복되지 않는다", () => {
  const result = fixture("result_final.json"); // 내 차 2.33~5.73, 상대 차 2.33~6.93, 내 차 5.8~6.4, 접촉 5.87~6.47
  const moments = toMoments(result);
  assert.equal(moments.length, 2);
  assert.equal(moments[0].summary, "내 차의 움직임 · 상대 차 확인");
  assert.match(moments[0].title, /내 차가 움직이고 있었어요\. 상대 차가 화면에 보이는 구간이에요\./);
  assert.equal(moments[0].tag, "확인됨");
  assert.equal(moments[1].summary, "접촉 근거");
  assert.equal(moments[1].tone, "impact");
  assert.equal(new Set(moments.map((m) => m.title)).size, moments.length); // 문장이 서로 다르다
  assert.ok(moments.every((m) => !m.title.includes("A(") && !m.title.includes("추정됨")), "모델 내부 표현이 남지 않는다");
});

test("타임라인: 사고 흐름이 있으면 접근 → 사고 직전 → 접촉 → 접촉 이후 단계로 보여 준다", () => {
  const flow = (stage, start, end, description, certainty = "관찰") => ({ kind: "사고 흐름", stage, actor: null, start_sec: start, end_sec: end, description, certainty });
  const result = {
    timeline: [
      { kind: "A 움직임", actor: "me", start_sec: 0, end_sec: 6, certainty: "이동 추정" },   // 사고 흐름이 있으면 따로 단계로 만들지 않는다
      flow("접촉", 3, 4, "접촉이 의심되는 장면이에요.", "추정"),
      flow("접근", 0, 2, "내 차가 직진하고 있어요."),
      flow("사고 직전", 2, 3, "상대 차가 오른쪽에서 가까워져요."),
    ],
    impact: {},
  };
  const moments = toMoments(result);
  assert.deepEqual(moments.map((m) => m.label), ["접근", "사고 직전", "접촉"]);
  assert.deepEqual(moments.map((m) => m.position), [0, 50, 100]);
  assert.equal(moments[2].tone, "impact");
  assert.equal(moments[2].tag, "AI 추정");
  assert.equal(moments[0].title, "내 차가 직진하고 있어요.");
  assert.equal(moments[0].summary, "사고 흐름 1 / 3");
  assert.equal(moments[0].range, "0~2초 (약 2초 동안)");
});

test("타임라인: 사고 흐름이 없는 예전 결과는 지금처럼 관찰 구간으로 보여 준다", () => {
  const moments = toMoments({ timeline: [{ kind: "A 움직임", actor: "me", start_sec: 0, end_sec: 5, certainty: "이동 추정" }], impact: {} });
  assert.equal(moments.length, 1);
  assert.equal(moments[0].summary, "내 차의 움직임");
});

test("타임라인: 구간 길이를 쉬운 말로 알려 준다", () => {
  const [moment] = toMoments({ timeline: [{ kind: "B 확인 구간", start_sec: 2.33, end_sec: 6.93, certainty: "구별됨" }], impact: {} });
  assert.equal(moment.range, "2.3~6.9초 (약 5초 동안)");
  const [instant] = toMoments({ timeline: [{ kind: "접촉 근거 구간", start_sec: 5, end_sec: 5, certainty: "접촉 추정" }], impact: {} });
  assert.equal(instant.range, "5초");
});

test("사고 유형 이름: 쉬운 말이 있으면 그것을, 없으면 과실표의 원래 이름을 쓴다", async () => {
  const { easyOf, easyLabel } = await import("./adapters.js");
  const option = { feature: "차로변경(진로변경)", my_progress: "후행 직진", easy: { feature: "차선 변경 사고", my_progress: "뒤따르던 차가 직진" } };
  assert.equal(easyOf(option, "feature"), "차선 변경 사고");
  assert.equal(easyOf({ feature: "차로변경(진로변경)" }, "feature"), "차로변경(진로변경)"); // 예전에 저장된 결과
  assert.equal(easyLabel([option], "my_progress", "후행 직진"), "뒤따르던 차가 직진");
  assert.equal(easyLabel([option], "my_progress", "모르는 값"), "모르는 값");
  assert.equal(easyOf(null, "feature"), "");
});

test("타임라인: 접촉이 확실하지 않으면 충돌 기준 표현을 쓰지 않는다", () => {
  const result = fixture("result_final.json");
  const moments = toMoments({ ...result, impact: { ...result.impact, confirmed: false } });
  assert.ok(moments.every((m) => !/^충돌 [\d.]+초/.test(m.label)));
  assert.ok(moments.some((m) => m.label === "충돌 의심 구간"));
});

test("타임라인이 비어 있어도 오류 없이 빈 목록", () => {
  assert.deepEqual(toMoments({ timeline: [], impact: {} }), []);
});

test("판례 카드: 퍼센트 없이 단계와 공통점·차이점을 보여 준다", () => {
  const cards = toCaseCards(fixture("result_final.json").related_cases);
  assert.equal(cards.length, 2);
  assert.equal(cards[0].matchLabel, "같은 사고 유형");
  assert.equal(cards[1].matchLabel, "조건 일부 일치");
  assert.equal(cards[0].verified, true);
  assert.equal(cards[1].verified, false);
  assert.ok(cards[0].comparison.common[0].text[0].length > 0);
  assert.ok(cards[0].comparison.differences.length > 0);
  for (const card of cards) assert.ok(!JSON.stringify({ ...card, sourceUrl: null }).includes("%"), "유사도 퍼센트를 만들지 않는다"); // 주소의 %EC 같은 인코딩은 제외
});

test("판례 카드: AI 비교는 제목·판결문 인용·판례 설명을 함께 보여 준다", () => {
  const [card] = toCaseCards([{
    case_id: "c1", court: "서울중앙지방법원", case_number: "2022나1", summary: "요약", source_kind: "law_api",
    comparison: {
      source: "ai", match_label: "조건 일부 일치", note: "AI가 비교했어요.", common: ["문장 하나"], differences: ["차이 하나"],
      common_items: [{ label: "방향지시등", text: "신호 없이 차로를 바꿨어요.", quote: "방향지시등을 켜지 않은 채" }],
      differences_items: [{ label: "내 사고만", text: "판례 본문에서는 확인되지 않아요.", quote: "" }],
    },
    digest: { overview: { text: "개요예요.", quote: "인용 구절" }, ruling_points: [{ text: "판단이에요.", quote: "판단 구절" }],
              laws: [{ label: "도로교통법 제19조", name: "도로교통법 제19조 (안전거리 확보 등)", easy: "쉬운 풀이" }] },
  }]);
  assert.equal(card.byAi, true);
  assert.deepEqual(card.comparison.common[0], { label: "방향지시등", text: ["신호 없이 차로를 바꿨어요."], quote: "방향지시등을 켜지 않은 채" });
  assert.equal(card.comparison.differences[0].quote, "");
  assert.equal(card.digest.overview.quote, "인용 구절");
  assert.equal(card.digest.points.length, 1);
  assert.equal(card.digest.laws[0].easy, "쉬운 풀이");
});

test("판례 카드: 규칙 비교는 공통점 1, 차이점 1 제목을 쓰고 판례 설명은 없다", () => {
  const [card] = toCaseCards([{ case_id: "c1", court: "법원", case_number: "1", comparison: { source: "rule", common: ["a"], differences: ["b", "c"] } }]);
  assert.equal(card.byAi, false);
  assert.equal(card.digest, null);
  assert.deepEqual(card.comparison.differences.map((d) => d.label), ["차이점 1", "차이점 2"]);
});

test("판례가 하나도 없어도 빈 목록", () => {
  assert.deepEqual(toCaseCards([]), []);
  assert.deepEqual(toCaseCards(undefined), []);
});

test("내 사고 요약", () => {
  assert.deepEqual(myAccidentPoints(fixture("result_final.json")).length, 3);
  assert.equal(myAccidentPoints(fixture("result_unresolved.json"))[0], "표에서 맞는 유형을 찾지 못한 사고");
});

test("결과 화면에 들어가기 전 안내: 상태마다 알맞은 문구와 이동 링크", async () => {
  const { describeAnalysis } = await import("./adapters.js");
  const session = { sessionId: "s", accidentId: "a" };
  assert.match(describeAnalysis({ session: null, analysisId: "x" }).title, /이 브라우저에서 만든 분석이 아니에요/);
  assert.equal(describeAnalysis({ session, error: { status: 404, message: "없음" }, analysisId: "x" }).retry, false);
  assert.equal(describeAnalysis({ session, error: { status: 500, message: "오류" }, analysisId: "x" }).retry, true);
  assert.match(describeAnalysis({ session, loading: true, analysisId: "x" }).title, /불러오는 중/);
  const processing = describeAnalysis({ session, analysis: { status: "processing", stage: { label: "전체 흐름 분석" } }, analysisId: "x" });
  assert.match(processing.body, /전체 흐름 분석/);
  const waiting = describeAnalysis({ session, analysis: { status: "awaiting_confirmation" }, analysisId: "abc" });
  assert.equal(waiting.link.to, "/upload?resume=abc");
  const unsupported = describeAnalysis({ session, analysis: { status: "unsupported", unsupported_reason: "차대보행자 사고는 지원하지 않습니다." }, analysisId: "x" });
  assert.equal(unsupported.title, "분석할 수 없는 영상이에요");
  assert.match(unsupported.body, /^차대보행자 사고는 지원하지 않습니다\./);
  assert.equal(unsupported.link.to, "/upload");
  assert.equal(describeAnalysis({ session, analysis: { status: "failed", error: { message: "실패했어요" } }, analysisId: "x" }).body, "실패했어요");
});

test("취소한 분석은 실패가 아니라 취소했다고 알리고 새 영상 올리기로 안내한다", async () => {
  const { describeAnalysis } = await import("./adapters.js");
  const session = { sessionId: "s", accidentId: "a" };
  const cancelled = describeAnalysis({ session, analysis: { status: "failed", error: { code: "CANCELLED", message: "분석을 취소했어요." } }, analysisId: "x" });
  assert.equal(cancelled.title, "분석을 취소했어요");
  assert.equal(cancelled.link.to, "/upload");
  const failed = describeAnalysis({ session, analysis: { status: "failed", error: { code: "ANALYSIS_FAILED", message: "실패했어요" } }, analysisId: "x" });
  assert.equal(failed.title, "분석하지 못했어요");
});

test("세션이 끝난 분석은 삭제됐다고 알리고 새 영상 올리기로 안내한다", async () => {
  const { describeAnalysis } = await import("./adapters.js");
  for (const input of [{ session: null, expired: true }, { session: { sessionId: "s" }, error: { code: "SESSION_EXPIRED" } }]) {
    const notice = describeAnalysis({ analysis: null, analysisId: "x", ...input });
    assert.match(notice.title, /삭제됐어요/);
    assert.equal(notice.link.to, "/upload");
  }
});

test("AI가 본 상황: 내부 표기 대신 쉬운 말로 풀고, 모르는 값은 모른다고 말한다", async () => {
  const { easySituation, easySituationLine } = await import("./adapters.js");
  const rows = easySituation({ road_shape: "직선 도로", my_action: "직진", other_action: "정지/대기", contact: "충돌 정황 강함" });
  assert.deepEqual(rows.map((r) => r.label), ["도로", "내 차", "상대 차", "접촉"]);
  assert.equal(rows[1].text, "직진하는 중");
  assert.equal(rows[2].text, "멈춰 있거나 기다리는 중");
  assert.match(rows[3].text, /부딪혔을 가능성이 높은 장면/);
  // 미확인·기타·빈 값은 미리 채운 것처럼 보이지 않게 한다
  const unsure = easySituation({ road_shape: "", my_action: "미확인", other_action: "기타", contact: "판단 불가" });
  assert.deepEqual(unsure.slice(0, 3).map((r) => r.text), ["AI가 알아보지 못했어요", "AI가 알아보지 못했어요", "AI가 알아보지 못했어요"]);
  // 처음 보는 값은 원문을 그대로 보여 준다
  assert.equal(easySituation({ my_action: "새로운동작" })[1].text, "새로운동작");
  // 구조화된 값이 없는 예전 결과는 null, 한 줄 문장은 서버 요약으로 되돌아간다
  assert.equal(easySituation(undefined), null);
  assert.equal(easySituation({}), null);
  assert.equal(easySituationLine({}, "서버 요약"), "서버 요약");
  assert.match(easySituationLine({ my_action: "직진" }, "x"), /^AI가 영상에서 본 모습\(추정\) — 도로: AI가 알아보지 못했어요 · 내 차: 직진하는 중/);
});

test("결과 화면 문구는 모델의 내부 요약이 아니라 쉬운 말 문장을 쓴다", () => {
  const result = fixture("result_final.json");
  const desc = toReportModel(result, "abcdef12").header.desc;
  assert.ok(desc.startsWith("AI가 영상에서 본 모습(추정)"));
  assert.ok(!desc.includes("도로 형태:"));
  assert.equal(toReportModel({ ...result, situation: undefined }, "abcdef12").header.desc, result.summary);
});

test("고른 상황이 AI 관찰과 어긋날 때만 안내하고, 어떤 점이 다른지 보여 준다", async () => {
  const { toSituationCheck } = await import("./adapters.js");
  assert.equal(toSituationCheck(fixture("result_final.json")), null);
  assert.equal(toSituationCheck({ situation_check: { conflict: false, items: [] } }), null);
  const check = toSituationCheck({ situation_check: { conflict: true, items: [{ who: "other", ai_action: "정지/대기", chosen: "앞차가 차로를 바꿈" }, { who: "me", ai_action: "미확인", chosen: "직진" }] } });
  assert.match(check.title, /달라요/);
  assert.match(check.body, /참고용으로만/);
  assert.deepEqual(check.lines, [
    "상대 차 — AI가 본 모습: 멈춰 있거나 기다리는 중 / 고르신 내용: 앞차가 차로를 바꿈",
    "내 차 — AI가 본 모습: AI가 알아보지 못했어요 / 고르신 내용: 직진",
  ]);
  const model = toReportModel({ ...fixture("result_final.json"), situation_check: { conflict: true, items: [{ who: "me", ai_action: "직진", chosen: "좌회전" }] } }, "abcdef12");
  assert.equal(model.situationCheck.lines.length, 1);
  assert.equal(toReportModel(fixture("result_final.json"), "abcdef12").situationCheck, null);
});

test("선택지가 하나뿐인 항목은 앞 항목이 정해진 뒤에 자동으로 채운다", () => {
  const empty = { place: "", feature: "", my_progress: "", other_progress: "" };
  // 아무것도 안 골랐으면 장소는 여러 개라서 채우지 않는다
  assert.deepEqual(autoFill(items, empty), empty);
  const place = cascade(items, empty).place[0];
  const feature = cascade(items, { ...empty, place }).feature[0];
  const base = { ...empty, place, feature };
  // 내 차 움직임까지 고른 뒤 상대 차 선택지가 하나면 상대 차는 정해진다
  const my = cascade(items, base).my_progress.find((value) => cascade(items, { ...base, my_progress: value }).other_progress.length === 1);
  assert.ok(my, "상대 차 선택지가 하나뿐인 경우가 있다");
  const filled = autoFill(items, { ...base, my_progress: my });
  assert.ok(filled.other_progress);
  assert.ok(resolveOption(items, filled), "네 항목이 모두 정해져 유형과 내 차 역할이 나온다");
  // 앞 항목이 비어 있으면 뒤 항목은 채우지 않는다 (선택을 바꿔 다시 비운 경우)
  assert.equal(autoFill(items, { ...empty, place }).my_progress, "");
  // 이미 고른 값은 건드리지 않고, 원래 selection 객체도 바꾸지 않는다
  const chosen = { ...base, my_progress: my, other_progress: filled.other_progress };
  assert.deepEqual(autoFill(items, chosen), chosen);
  assert.equal(base.my_progress, "");
  // 장소가 하나뿐이면 장소도 정해진다
  const onePlace = items.filter((item) => item.place === place);
  assert.equal(autoFill(onePlace, empty).place, place);
});

test("내 차의 움직임만 고르면 과실표의 A/B 역할은 사용자에게 묻지 않고도 정해진다", () => {
  // 같은 장소·사고 유형에서 내 차 움직임이 서로 다르면 서로 다른 선택지(역할 포함)가 나온다
  const empty = { place: "직선 도로", feature: "차로변경(진로변경)", my_progress: "", other_progress: "" };
  const mine = cascade(items, empty).my_progress;
  assert.ok(mine.length >= 2);
  const picks = mine.map((value) => resolveOption(items, autoFill(items, { ...empty, my_progress: value })));
  assert.ok(picks.every(Boolean), "내 차 움직임만 골라도 하나의 선택지로 정해진다");
  assert.ok(picks.every((option) => option.role === "A" || option.role === "B"));
});

test("AI가 유형을 확정하지 못해도 후보들이 같은 장소를 가리키면 그 장소만 미리 고른다", () => {
  const cand = (place, feature) => ({ place, feature, my_progress: "x", other_progress: "y" });
  assert.equal(commonSelection([]), null);
  assert.equal(commonSelection(undefined), null);
  // 장소와 사고 유형이 모두 같으면 둘 다, 움직임은 비워 둔다
  assert.deepEqual(commonSelection([cand("사거리 교차로(신호등 있음)", "a"), cand("사거리 교차로(신호등 있음)", "a")]), { place: "사거리 교차로(신호등 있음)", feature: "a", my_progress: "", other_progress: "" });
  // 장소만 같으면 장소만
  assert.deepEqual(commonSelection([cand("사거리 교차로(신호등 있음)", "a"), cand("사거리 교차로(신호등 있음)", "b")]), { place: "사거리 교차로(신호등 있음)", feature: "", my_progress: "", other_progress: "" });
  // 장소가 다르면 아무것도 고르지 않는다 (사고 유형 이름이 같아도 장소가 다르면 다른 것이다)
  assert.deepEqual(commonSelection([cand("직선 도로", "a"), cand("주차장(또는 차도가 아닌 장소)", "a")]), { place: "", feature: "", my_progress: "", other_progress: "" });
});

test("AI가 본 모습: 검증은 못 통과했지만 모델이 기록한 움직임은 '추정'으로 보여 준다", () => {
  const rows = easySituation({ road_shape: "교차로", my_action: "미확인", other_action: "미확인", my_action_hint: "좌회전", other_action_hint: null, contact: "접촉 추정" });
  assert.equal(rows[1].text, "좌회전하는 중 (추정)");
  assert.equal(rows[2].text, "AI가 알아보지 못했어요");
  // 검증된 값이 있으면 힌트와 상관없이 그 값을 쓴다
  assert.equal(easySituation({ my_action: "직진", my_action_hint: "좌회전" })[1].text, "직진하는 중");
  // 힌트만 있어도 구조화된 값이 있는 것으로 본다
  assert.ok(easySituation({ other_action_hint: "직진" }));
});
