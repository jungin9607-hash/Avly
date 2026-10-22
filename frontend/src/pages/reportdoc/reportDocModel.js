// 보고서(인쇄용 문서) 화면이 읽는 모양. 서버 결과(result)를 문서의 절(요약, 사고 상황, 산정 과정, 타임라인, 판례, 법령, 유의사항)로 바꾼다.
// 서버가 주지 않은 값은 만들어 넣지 않는다. 값이 없는 절은 비워 두거나 "없어요"라고 말한다.
import { easyOf, easySituationLine, toCaseCards, toMoments, toSituationCheck } from "../../api/adapters.js";

const HEADLINE = {
  final: "AI 예상 과실 비율",
  partial: "확인한 요소만 반영한 예상 비율",
  base_only: "기본 비율 (비율이 달라지는 사정이 등록되지 않은 유형)",
  unresolved: "과실 비율을 안내할 수 없어요",
};

const HEADLINE_NOTE = {
  final: "비율이 달라지는 사정을 모두 확인해서 계산한 예상 비율이에요. 실제 비율은 보험사 합의나 법원 판단에 따라 달라질 수 있어요.",
  partial: "아직 확인하지 못한 사정이 있어서 실제 비율은 달라질 수 있어요.",
  base_only: "이 사고 유형은 검수가 끝난 가감요소가 아직 없어서 기본 비율만 안내해요.",
  unresolved: "과실표에서 맞는 사고 유형을 찾지 못했어요. 아래 상황 설명만 참고해 주세요.",
};

const CONTACT_TEXT = {
  "접촉 관찰": "접촉한 장면이 관찰됐어요.",
  "충돌 정황 강함": "충돌 정황이 강하게 보여요. 직접 접촉이 확인된 것과는 구분돼요.",
  "접촉 추정": "접촉이 의심돼요. 접촉 여부는 확인이 필요해요.",
  "근접만 관찰": "두 차가 가까워진 장면만 확인됐어요.",
  "판단 불가": "접촉했는지 판단하기 어려웠어요.",
};

const NO_REASON = "해당 요소 없음으로 확인";

// 같은 항목이 내 차와 상대 차에 모두 있을 수 있어서 누구 이야기인지 앞에 붙인다
const withWho = (item) => (item.who ? `${item.who}: ${item.title}` : item.title);

export const LAW_FALLBACK = "조문의 쉬운 풀이를 준비하고 있어요. 국가법령정보센터에서 원문을 확인해 주세요.";

export function formatDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("ko-KR", { year: "numeric", month: "long", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function headlineOf(result) {
  const state = result.state;
  const fault = result.fault;
  const pair = state === "final" ? fault?.final : state === "partial" ? fault?.adjusted : state === "base_only" ? fault?.base : null;
  return { title: HEADLINE[state] ?? HEADLINE.base_only, note: result.explanation?.status || HEADLINE_NOTE[state] || "", me: pair?.me ?? null, other: pair?.other ?? null };
}

function situationRows(result) {
  const type = result.accident_type;
  const rows = [];
  if (type) {
    rows.push(["사고 장소", easyOf(type, "place")], ["사고 유형", easyOf(type, "feature")], ["내 차의 움직임", easyOf(type, "my_progress")], ["상대 차의 움직임", easyOf(type, "other_progress")]);
  } else {
    const s = result.situation ?? {};
    if (s.road_shape) rows.push(["도로 형태(AI 관찰)", s.road_shape]);
    if (s.my_action) rows.push(["내 차의 움직임(AI 관찰)", s.my_action]);
    if (s.other_action) rows.push(["상대 차의 움직임(AI 관찰)", s.other_action]);
  }
  const contact = result.situation?.contact;
  if (contact) rows.push(["접촉 판단", CONTACT_TEXT[contact] ?? contact]);
  return rows;
}

function officialType(result) {
  const t = result.accident_type;
  return t ? `${t.place} · ${t.feature} · 내 차 ${t.my_progress} / 상대 차 ${t.other_progress}` : null;
}

// 맨 위 결론 박스의 한 줄 설명. 확정된 사고 유형이 있으면 그것으로 문장을 만들고, 없으면 서버가 준 요약(AI의 관찰 메모)을 쓴다.
function oneLineOf(result) {
  const t = result.accident_type;
  if (t) return `${easyOf(t, "place")}에서 일어난 사고예요. 내 차는 ${easyOf(t, "my_progress")}, 상대 차는 ${easyOf(t, "other_progress")} 상황이에요.`;
  return easySituationLine(result.situation, result.summary ?? "");
}

// 고른 상황이 AI 의 관찰과 어긋나면 타임라인 절에 한 줄로 알린다(타임라인은 AI 가 본 그대로이므로)
function situationCheckNote(result) {
  const check = toSituationCheck(result);
  return check ? `${check.title}. ${check.body}` : "";
}

function candidateLines(result) {
  if (result.state !== "unresolved") return [];
  return (result.reference_candidates ?? []).slice(0, 3).map((c) => `${easyOf(c, "place")} · ${easyOf(c, "feature")} (내 차 ${easyOf(c, "my_progress")} / 상대 차 ${easyOf(c, "other_progress")})`);
}

function caseView(card) {
  return {
    heading: [card.court, card.date, card.caseNumber].filter(Boolean).join(" · "),
    category: card.category,
    matchLabel: card.matchLabel,
    summary: card.summary,
    common: card.comparison.common.slice(0, 2).map((i) => i.text.join(" ")),
    differences: card.comparison.differences.slice(0, 2).map((i) => i.text.join(" ")),
    limit: card.limit,
    unverified: !card.verified,
    byAi: card.byAi,
    sourceUrl: card.sourceUrl,
  };
}

export function toReportDocument(result, { analysisId, createdAt, expiresAt } = {}) {
  const state = result.state;
  const cards = toCaseCards(result.related_cases);
  const moments = toMoments(result);
  return {
    meta: {
      code: String(analysisId ?? "").slice(0, 8),
      createdAt: formatDateTime(createdAt),
      expiresAt: formatDateTime(expiresAt),
    },
    notice: result.notice ?? "",
    headline: { ...headlineOf(result), oneLine: oneLineOf(result) },
    summary: easySituationLine(result.situation, result.summary ?? ""),
    situation: { rows: situationRows(result), official: officialType(result), candidates: candidateLines(result) },
    steps: state === "unresolved" ? [] : (result.steps ?? []).map((s) => ({
      base: s.kind === "base",
      title: s.kind === "base" ? "기본 비율" : s.title,
      detail: s.kind === "base" ? (s.easy ?? "") : (s.easy ?? ""),
      change: s.kind === "base" ? "" : (s.effect ?? ""),
      me: s.me,
      other: s.other,
    })),
    pending: (result.adjustments?.pending ?? []).map((p) => ({ title: withWho(p), question: p.question ?? "" })),
    // 사용자가 '아니요'로 답한 항목은 한 줄로 모으고, 그 밖의 이유로 적용하지 않은 항목만 이유와 함께 보여 준다
    answeredNo: (result.adjustments?.not_applied ?? []).filter((p) => p.reason === NO_REASON).map(withWho),
    notApplied: (result.adjustments?.not_applied ?? []).filter((p) => p.reason !== NO_REASON).map((p) => ({ title: withWho(p), reason: p.reason ?? "" })),
    timeline: { rows: moments.map((m) => ({ label: m.label, range: m.range, title: m.title, tag: m.tag })), note: [result.timeline_note, situationCheckNote(result)].filter(Boolean).join(" ") },
    cases: cards.slice(0, 3).map(caseView),
    laws: (result.laws ?? []).map((l) => ({ name: l.name ?? l.label, easy: l.easy ?? LAW_FALLBACK })),
    sources: [...new Set(["손해보험협회 과실비율 인정기준(2023.06)", ...cards.map((c) => c.category).filter(Boolean)])],
  };
}
