// 서버 응답을 기존 화면 컴포넌트가 읽는 모양으로 바꾸는 순수 함수들. (화면도, 서버 호출도 여기에 없다)
import { ROUTES } from "../routes.js";

// ---------------------------------------------------------------- 사고 상황 확인 (장소 → 사고 유형 → 내 차 → 상대 차)
const LEVELS = ["place", "feature", "my_progress", "other_progress"];

export const LEVEL_LABEL = {
  place: "사고 장소",
  feature: "사고 유형",
  my_progress: "내 차의 움직임",
  other_progress: "상대 차의 움직임",
};

const unique = (values) => [...new Set(values)];

// 사고 유형 이름: 서버가 쉬운 말(option.easy)을 함께 준다. 없으면(예전에 저장된 결과) 과실표의 원래 이름을 그대로 쓴다.
export const easyOf = (option, level) => option?.easy?.[level] || option?.[level] || "";

// 선택 목록의 값(원래 이름)에 보여 줄 쉬운 말
export function easyLabel(items, level, value) {
  const found = items.find((item) => item[level] === value);
  return found ? easyOf(found, level) : value;
}

// selection 의 앞 항목들과 맞는 선택지만 남긴다.
function matching(items, selection, upTo) {
  return items.filter((item) => LEVELS.slice(0, upTo).every((level) => item[level] === selection[level]));
}

// 각 항목에서 고를 수 있는 값. 앞 항목을 바꾸면 뒤 항목의 보기가 좁혀진다.
export function cascade(items, selection) {
  return Object.fromEntries(
    LEVELS.map((level, index) => [level, unique(matching(items, selection, index).map((item) => item[level]))]),
  );
}

// 네 항목이 모두 정해지면 선택지 하나(유형 번호와 내 차가 표에서 맡은 쪽 포함)로 돌려준다. 아직이면 null.
export function resolveOption(items, selection) {
  if (!LEVELS.every((level) => selection[level])) return null;
  return matching(items, selection, LEVELS.length)[0] ?? null;
}

// 앞 항목이 바뀌어 더는 고를 수 없게 된 뒤 항목의 선택을 지운다.
export function normalizeSelection(items, selection) {
  const next = { ...selection };
  const options = cascade(items, next);
  for (const level of LEVELS) {
    if (next[level] && !options[level].includes(next[level])) {
      for (const later of LEVELS.slice(LEVELS.indexOf(level))) next[later] = "";
      break;
    }
    options[level] = cascade(items, next)[level];
  }
  return next;
}

export function selectionFrom(option) {
  return option ? Object.fromEntries(LEVELS.map((level) => [level, option[level]])) : Object.fromEntries(LEVELS.map((level) => [level, ""]));
}

// ---------------------------------------------------------------- 분석 진행 단계
export const STAGE_LABELS = [
  { id: "plate_masking", label: "번호판·사람 가리기" },
  { id: "overview", label: "전체 흐름 분석" },
  { id: "detail_review", label: "사고 전후 상세 확인" },
  { id: "case_matching", label: "과실 유형 비교" },
];

// 지금 진행 중인 단계의 위치. 아직 시작 전이면 -1. 단계 id 를 모르면 -1.
export function stageIndex(stageId) {
  return STAGE_LABELS.findIndex((stage) => stage.id === stageId);
}

// ---------------------------------------------------------------- 결과 화면
// 과실 단계 카드(StepRatio, FactorCard)가 읽는 모양: { title, tag, ratio: [내 과실, 상대 과실], body, legal }
export function toSteps(result) {
  const laws = (result.laws ?? []).map((law) => ({
    name: law.name ?? law.label,
    text: law.easy ?? "조문의 쉬운 풀이를 준비하고 있어요. 국가법령정보센터에서 원문을 확인해 주세요.",
  }));
  return result.steps.map((step, index) => ({
    title: step.title,
    tag: step.kind === "base" ? "출발점" : step.effect,
    ratio: [step.me, step.other],
    body: step.easy ?? "",
    legal: index === 0 ? laws : [],
  }));
}

const FACTOR_DESC = {
  final: (n) => (n > 0 ? `${n}가지 가감요소를 반영했어요. 어려운 법적 근거는 눌러서 볼 수 있어요.` : "반영할 가감요소가 없어서 기본 비율 그대로예요."),
  partial: (n) => (n > 0 ? "확인한 가감요소만 반영했어요. 확인하지 못한 요소가 있어서 실제 비율은 달라질 수 있어요." : "적용된 가감요소가 없어서 기본 비율 그대로예요. 확인하지 못한 요소가 있어서 실제 비율은 달라질 수 있어요."),
  base_only: () => "이 사고 유형은 가감요소가 아직 등록되지 않아 기본 비율만 안내해요.",
};

// 결과 화면 맨 위 문구와 상태별 안내
export function toReportModel(result, analysisId) {
  const state = result.state;
  const type = result.accident_type;
  const applied = result.adjustments?.applied?.length ?? 0;
  return {
    state,
    header: {
      title: "과실 분석 결과",
      desc: result.summary ?? "블랙박스 영상을 분석해 산정한 과실 비율과 그 근거예요.",
      keywords: type ? [easyOf(type, "place"), easyOf(type, "feature"), `식별 코드 ${String(analysisId ?? "").slice(0, 8)}`] : [`식별 코드 ${String(analysisId ?? "").slice(0, 8)}`],
    },
    appliedCount: applied,
    factorHeader: { kicker: "판단 근거", desc: (FACTOR_DESC[state] ?? FACTOR_DESC.base_only)(applied) },
    statusText: result.explanation?.status ?? "",
    steps: state === "unresolved" ? [] : toSteps(result),
    // 맨 위 큰 비율에 보여 줄 값: 확정이면 최종, 아니면 지금까지 반영한 값 (마지막 단계)
    shown: state === "unresolved" ? null : result.steps[result.steps.length - 1],
    final: result.fault?.final ?? null,
    pending: result.adjustments?.pending ?? [],
    candidates: result.reference_candidates ?? [],
    notice: result.notice,
  };
}

// ---------------------------------------------------------------- 타임라인
// 서버의 타임라인은 AI 가 기록한 관찰 구간(내 차의 움직임, 상대 차 확인, 접촉 근거)을 하나씩 담는다. 구간끼리 겹치고 시작 시각이 거의 같은 것이 많아서
// 그대로 한 단계씩 보여 주면 같은 장면이 반복된다. 그래서 (1) 같은 상태가 끊겨서 이어지는 내 차의 움직임은 하나로 합치고
// (2) 시작 시각이 비슷한 관찰은 한 단계로 묶는다. 문장은 AI 의 관찰을 그대로 옮기되 쉬운 말로 미리 정해 둔 것을 쓴다(AI 가 새로 쓰지 않는다).
const KIND_LABEL = { "A 움직임": "내 차의 움직임", "B 확인 구간": "상대 차 확인", "접촉 근거 구간": "접촉 근거" };
const KIND_ORDER = { "A 움직임": 0, "B 확인 구간": 1, "접촉 근거 구간": 2 };
const MERGE_SEC = 0.5; // 이 시간(초) 안에서 이어지거나 함께 시작하는 관찰은 하나로 본다

const SENTENCES = {
  "A 움직임": {
    "이동 추정": "내 차가 움직이고 있었어요.",
    "정지 추정": "내 차가 멈춰 있었어요.",
    default: "내 차가 움직였는지는 영상만으로 알기 어려워요.",
  },
  "B 확인 구간": {
    구별됨: "상대 차가 화면에 보이는 구간이에요.",
    default: "상대 차로 보이는 차가 화면에 나오는 구간이에요. 어느 차인지는 더 확인이 필요해요.",
  },
  "접촉 근거 구간": {
    "접촉 관찰": "내 차와 상대 차가 부딪힌 장면으로 보여요.",
    "충돌 정황 강함": "부딪혔을 가능성이 높은 장면이에요. 실제로 닿았는지는 확인이 필요해요.",
    "접촉 추정": "부딪혔을 수 있는 장면이에요. 접촉 여부는 확인이 필요해요.",
    "근접만 관찰": "두 차가 가까이 있었지만 부딪혔는지는 확인되지 않았어요.",
    default: "접촉했는지 판단하기 어려운 장면이에요.",
  },
};
// 화면의 작은 표시. AI 가 확정한 것이 아니라 추정인 것은 그렇게 보이게 한다.
const TAG = {
  "이동 추정": "AI 추정", "정지 추정": "AI 추정", 구별됨: "확인됨", "접촉 관찰": "접촉 관찰", "충돌 정황 강함": "충돌 의심",
  "접촉 추정": "접촉 추정", "근접만 관찰": "근접만 관찰", "판단 불가": "판단 어려움",
};

const round1 = (value) => Math.round(value * 10) / 10;

function sentenceOf(event) {
  const table = SENTENCES[event.kind];
  return table ? (table[event.certainty] ?? table.default) : (event.description ?? "");
}

// 같은 상태가 끊겨서 이어지는 내 차의 움직임(예: 이동 추정 두 구간)을 하나로 합친다
function mergeMovement(events) {
  const rest = events.filter((e) => e.kind !== "A 움직임");
  const merged = [];
  for (const event of events.filter((e) => e.kind === "A 움직임").sort((a, b) => a.start_sec - b.start_sec)) {
    const last = merged[merged.length - 1];
    if (last && last.certainty === event.certainty && event.start_sec - last.end_sec <= MERGE_SEC) last.end_sec = Math.max(last.end_sec, event.end_sec);
    else merged.push({ ...event });
  }
  return [...rest, ...merged];
}

// 시작 시각이 비슷한 관찰을 한 묶음으로. 묶음 안에서는 내 차 → 상대 차 → 접촉 순서
function groupByStart(events) {
  const sorted = [...events].sort((a, b) => a.start_sec - b.start_sec || (KIND_ORDER[a.kind] ?? 9) - (KIND_ORDER[b.kind] ?? 9));
  const groups = [];
  for (const event of sorted) {
    const group = groups[groups.length - 1];
    if (group && event.start_sec - group[0].start_sec <= MERGE_SEC) group.push(event);
    else groups.push([event]);
  }
  return groups;
}

function rangeText(start, end) {
  const length = end - start;
  if (length < 0.05) return `${round1(start)}초`;
  return length >= 1 ? `${round1(start)}~${round1(end)}초 (약 ${Math.round(length)}초 동안)` : `${round1(start)}~${round1(end)}초`;
}

// Time 화면이 읽는 모양: { id, label, time, summary, tag, title, hud, tone }
// impact.confirmed 일 때만 "충돌 N초 전"처럼 충돌 시점을 기준으로 말한다. 아니면 영상 시각만 보여 준다.
export function toMoments(result) {
  const impact = result.impact ?? {};
  const groups = groupByStart(mergeMovement(result.timeline ?? []));
  return groups.map((group, index) => {
    const start = group[0].start_sec;
    const end = Math.max(...group.map((e) => e.end_sec));
    const contact = group.some((e) => e.kind === "접촉 근거 구간");
    // 시간축 위치는 순서대로 고르게 나눈다. 구간 시작 시각이 서로 가까우면 글자가 겹쳐서 읽을 수 없다.
    const position = groups.length > 1 ? (index / (groups.length - 1)) * 100 : 0;
    let label = `${round1(start)}초`;
    if (impact.confirmed && impact.sec != null) {
      const gap = round1(impact.sec - start);
      if (contact) label = "충돌 시점";
      else if (gap > 0) label = `충돌 ${gap}초 전`;
      else if (gap < 0) label = `충돌 ${-gap}초 후`;
    } else if (contact) {
      label = "충돌 의심 구간";
    }
    const lead = [...group].sort((a, b) => (KIND_ORDER[b.kind] ?? 0) - (KIND_ORDER[a.kind] ?? 0))[0]; // 접촉 > 상대 차 > 내 차
    return {
      id: `e${index}`,
      label,
      time: start,
      endTime: end,
      range: rangeText(start, end),
      position,
      summary: group.map((e) => KIND_LABEL[e.kind] ?? e.kind).join(" · "),
      tag: TAG[lead.certainty] ?? lead.certainty ?? "",
      title: group.map(sentenceOf).join(" "),
      evidence: [...new Set(group.map((e) => e.evidence_text).filter(Boolean))].join(" / "),
      hud: "CAM_FRONT",
      tone: contact ? "impact" : undefined,
    };
  });
}

// ---------------------------------------------------------------- 유사 판례
const SOURCE_LABEL = { knia_chart: "손해보험협회 도표 요약", law_api: "법령정보 API", manual: "직접 입력" };

// 비교 항목: AI 가 만든 항목(제목·문장·판결문 인용)이 있으면 그것을, 없으면 규칙이 만든 문장을 "공통점 1" 같은 제목으로 보여 준다
function toCompareItems(items, texts, prefix) {
  if (items?.length) return items.map((i) => ({ label: i.label, text: [i.text], quote: i.quote ?? "" }));
  return (texts ?? []).map((text, i) => ({ label: `${prefix} ${i + 1}`, text: [text], quote: "" }));
}

// AI 가 판례 본문을 읽고 정리한 설명. 없으면 null
function toDigest(digest) {
  if (!digest) return null;
  const points = (digest.ruling_points ?? []).map((p) => ({ text: p.text, quote: p.quote }));
  const laws = (digest.laws ?? []).map((l) => ({ label: l.label, name: l.name ?? "", easy: l.easy ?? "" }));
  if (!digest.overview && points.length === 0 && laws.length === 0) return null;
  return { overview: digest.overview ? { text: digest.overview.text, quote: digest.overview.quote } : null, points, laws };
}

// Law 화면 카드가 읽는 모양
export function toCaseCards(relatedCases) {
  return (relatedCases ?? []).map((item, index) => ({
    id: item.case_id ?? String(index),
    court: item.court,
    date: item.date ?? "선고일 미상",
    caseNumber: item.case_number,
    category: item.source_label ?? SOURCE_LABEL[item.source_kind] ?? "",
    matchLabel: item.comparison?.match_label ?? "",
    summary: item.summary,
    verified: Boolean(item.verified),
    sourceUrl: item.source_url ?? null,
    limit: item.comparison_limit ?? "",
    note: item.comparison?.note ?? "",
    factors: item.comparison?.common ?? [],
    byAi: item.comparison?.source === "ai",
    digest: toDigest(item.digest),
    comparison: {
      common: toCompareItems(item.comparison?.common_items, item.comparison?.common, "공통점"),
      differences: toCompareItems(item.comparison?.differences_items, item.comparison?.differences, "차이점"),
    },
  }));
}

export function myAccidentPoints(result) {
  const type = result.accident_type;
  return type ? [easyOf(type, "feature"), `내 차: ${easyOf(type, "my_progress")}`, `상대 차: ${easyOf(type, "other_progress")}`] : ["표에서 맞는 유형을 찾지 못한 사고"];
}

// ---------------------------------------------------------------- 결과 화면에 들어가기 전 안내
// 지금 상태에 맞는 안내 문구
export function describeAnalysis({ session, analysis, error, loading, analysisId, expired = false }) {
  if (expired || error?.code === "SESSION_EXPIRED") {
    return {
      title: "보관 시간이 지나 결과가 삭제됐어요",
      body: "개인정보를 지키려고 분석 결과와 영상은 일정 시간이 지나면 자동으로 삭제돼요. 새 영상으로 다시 분석해 주세요.",
      link: { to: ROUTES.home, label: "새 영상 올리기" },
    };
  }
  if (!session) {
    return { title: "이 브라우저에서 만든 분석이 아니에요", body: "분석 결과는 영상을 올린 브라우저에서만 볼 수 있어요. 영상을 다시 올려 분석해 주세요." };
  }
  if (error) return { title: "결과를 불러오지 못했어요", body: error.message, retry: error.status !== 404 };
  if (loading || !analysis) return { title: "결과를 불러오는 중이에요" };
  switch (analysis.status) {
    case "queued":
    case "processing":
      return { title: "아직 분석하고 있어요", body: analysis.stage ? `지금은 '${analysis.stage.label}' 단계예요. 끝나면 이 화면이 자동으로 바뀌어요.` : "곧 시작해요. 끝나면 이 화면이 자동으로 바뀌어요." };
    case "awaiting_confirmation":
      return { title: "사고 상황을 확인해 주세요", body: "분석은 끝났어요. 사고 상황을 확인하면 결과를 볼 수 있어요.", link: { to: ROUTES.resume(analysisId), label: "이어서 확인하기" } };
    case "unsupported":
      return {
        title: "분석할 수 없는 영상이에요",
        body: `${analysis.unsupported_reason} 에블리는 차량끼리 부딪힌 사고(차대차)만 분석할 수 있어요. 올리신 영상은 하루 안에 삭제돼요.`,
        link: { to: ROUTES.home, label: "다른 영상 올리기" },
      };
    case "failed":
      return { title: "분석하지 못했어요", body: analysis.error?.message };
    default:
      return { title: "결과를 볼 수 없어요" };
  }
}
