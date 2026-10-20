// 실행: node --test src/api/adapters.test.js   (Node 내장 테스트 도구. 추가 설치가 필요 없다)
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  cascade, myAccidentPoints, normalizeSelection, resolveOption, selectionFrom, stageIndex, toCaseCards, toMoments, toReportModel, toSteps,
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

test("세션이 끝난 분석은 삭제됐다고 알리고 새 영상 올리기로 안내한다", async () => {
  const { describeAnalysis } = await import("./adapters.js");
  for (const input of [{ session: null, expired: true }, { session: { sessionId: "s" }, error: { code: "SESSION_EXPIRED" } }]) {
    const notice = describeAnalysis({ analysis: null, analysisId: "x", ...input });
    assert.match(notice.title, /삭제됐어요/);
    assert.equal(notice.link.to, "/upload");
  }
});
