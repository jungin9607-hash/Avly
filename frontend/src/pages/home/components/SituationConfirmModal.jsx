import { useState } from "react";
import { autoFill, cascade, commonSelection, easyLabel, easyOf, easySituation, matching, normalizeSelection, resolveOption, selectionFrom } from "../../../api/adapters";
import CarLoader from "./CarLoader";
import ModalShell from "./ModalShell";

const LEVELS = ["place", "feature", "my_progress", "other_progress"];
const QUESTION = {
  place: "사고 장소",
  feature: "사고 유형",
  my_progress: "내 차는 어떻게 움직이고 있었습니까?",
  other_progress: "상대 차는 어떻게 움직이고 있었습니까?",
};

const PREVIOUS_HINT = { my_progress: "사고 유형", other_progress: "내 차의 움직임" };

// 3단계: AI 가 파악한 사고 상황을 사용자가 확인하고 고친다.
//   장소 → 사고 유형 → 내 차의 움직임 → 상대 차의 움직임 순서로 고르며, 앞 항목을 바꾸면 뒤 항목의 보기가 좁혀진다.
//   블랙박스 영상이므로 내 차는 항상 영상을 찍은 차다. 과실표의 A/B 는 사용자에게 묻지 않고, 고른 움직임으로 서버에 보낼 유형과 역할이 정해진다.
//   AI 가 확신한 후보가 있으면 미리 골라 두고 'AI 추정'을 붙인다. 참고 후보만 있거나 후보가 없으면 비워 둔다.
//   선택지가 하나뿐인 항목은 자동으로 정해진다.
//   맞는 유형이 없다고 답할 수도 있다 (그러면 과실 비율 없이 결과를 보여 준다).
export default function SituationConfirmModal({ situation, items: allItems, onChoose, onClose }) {
  // 동의 창에서 사고 장소를 골랐다면 그 장소의 유형만 보여 준다. 이미 고른 것을 다시 묻지 않는다.
  const placeHint = situation?.place_hint;
  const items = placeHint && allItems ? allItems.filter((item) => item.place.startsWith(placeHint)) : allItems;
  const allCandidates = situation?.candidates ?? [];
  const candidates = allCandidates.filter((c) => !placeHint || c.place.startsWith(placeHint));
  const preset = situation?.default_index != null && candidates.includes(allCandidates[situation.default_index]) ? allCandidates[situation.default_index] : null;
  // AI 가 유형을 확정하지 못했어도 후보들이 같은 장소를 가리키면 그 장소(와 유형)는 미리 골라 둔다
  const aiPick = preset ?? commonSelection(candidates);
  const [picked, setPicked] = useState(() => selectionFrom(aiPick));   // 사용자가 고른 값(AI 후보 포함). 자동으로 정해지는 값은 화면을 그릴 때마다 채운다
  const [none, setNone] = useState(false);

  if (!items) {
    return (
      <ModalShell title="AI가 분석한 사고 상황이 맞습니까?" progress={[3, 4]} onClose={onClose} sticky>
        <div className="md-analysis" role="status">
          <CarLoader />
          <p>선택지를 불러오는 중입니다.</p>
        </div>
      </ModalShell>
    );
  }

  const selection = autoFill(items, picked);
  const seen = easySituation(situation);
  const options = cascade(items, selection);
  const resolved = none ? null : resolveOption(items, selection);
  const ready = none || resolved;
  const pick = (level, value) => setPicked((current) => normalizeSelection(items, { ...current, [level]: value }));
  const otherCandidates = candidates.filter((c) => !(preset && c.accident_type_id === preset.accident_type_id && c.role === preset.role));
  const hasSignal = Boolean(selection.feature) && matching(items, selection, 2).some((item) => /신호/.test(`${item.my_progress}${item.other_progress}`));

  // 이 값을 AI 가 골랐는지(같은 쉬운 말이면 같은 값으로 본다)
  const sameAsAi = (level, value) => Boolean(aiPick?.[level] && value) && easyLabel(items, level, value) === easyLabel(items, level, aiPick[level]);
  // 항목 옆의 작은 표시: AI 가 고른 값 / 하나뿐이라 자동으로 정해진 값 / 사용자가 AI 와 다르게 고른 값
  const tagOf = (level) => {
    const value = selection[level];
    if (!value || none) return "";
    if (sameAsAi(level, value)) return "AI 추정";
    if (options[level].length === 1) return "자동 선택";
    return aiPick ? "직접 선택" : "";
  };

  return (
    <ModalShell
      title="AI가 분석한 사고 상황이 맞습니까?"
      desc="‘AI 추정’이 붙은 항목은 영상에서 파악한 내용입니다. 다르면 직접 골라 주시기 바랍니다."
      progress={[3, 4]}
      onClose={onClose}
      sticky
    >
      <div className="md-body">
        {(seen || situation?.summary) && (
          <section className="md-situation" aria-label="AI가 본 사고 상황">
            <details open={!preset}>
              <summary className="md-situation-label">AI가 영상에서 본 모습 (틀릴 수 있습니다)</summary>
              {seen ? (
                <ul className="md-situation-list">
                  {seen.map((row) => (
                    <li key={row.label}>
                      <b>{row.label}</b>
                      {row.text}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>{situation.summary}</p>
              )}
            </details>
          </section>
        )}
        {situation?.needs_check?.length > 0 && (
          <ul className="md-note">
            {situation.needs_check.map((text) => (
              <li key={text}>{text}</li>
            ))}
          </ul>
        )}

        {!preset && candidates.length > 0 && <p className="md-hint">AI가 확신하지 못했습니다. 아래 후보를 눌러 보거나 직접 골라 주시기 바랍니다.</p>}
        {otherCandidates.length > 0 && (
          <div className="md-chips" aria-label={preset ? "다른 후보" : "참고 후보"}>
            {otherCandidates.map((c) => (
              <button
                key={`${c.accident_type_id}-${c.role}`}
                type="button"
                className="md-chip"
                onClick={() => {
                  setNone(false);
                  setPicked(selectionFrom(c));
                }}
              >
                {easyOf(c, "feature")} · 내 차 {easyOf(c, "my_progress")}
              </button>
            ))}
          </div>
        )}

        <div className="md-fields">
          {LEVELS.map((level, index) => {
            const locked = none || (index > 0 && !selection[LEVELS[index - 1]]);
            const tag = tagOf(level);
            const head = (
              <span className="md-field-head">
                <b>{index + 1}</b>
                {QUESTION[level]}
                {tag && <em className={tag === "AI 추정" ? "md-ai-tag is-ai" : "md-ai-tag"}>{tag}</em>}
              </span>
            );
            if (index < 2) {
              return (
                <label key={level} className="md-field">
                  {head}
                  <select className="md-select" value={selection[level]} disabled={locked} onChange={(e) => pick(level, e.target.value)}>
                    <option value="">선택해 주시기 바랍니다</option>
                    {options[level].map((value) => (
                      <option key={value} value={value}>
                        {easyLabel(items, level, value)}
                        {sameAsAi(level, value) ? " (AI 추정)" : ""}
                      </option>
                    ))}
                  </select>
                </label>
              );
            }
            return (
              <div key={level} className="md-field" role="radiogroup" aria-label={QUESTION[level]}>
                {head}
                {locked ? (
                  <p className="md-note-text">{none ? "맞는 유형이 없다고 골랐습니다." : `${PREVIOUS_HINT[level]}을 먼저 골라 주시기 바랍니다.`}</p>
                ) : (
                  <div className="md-choices">
                    {options[level].map((value) => {
                      const on = easyLabel(items, level, value) === easyLabel(items, level, selection[level] || "");
                      return (
                        <button key={value} type="button" role="radio" aria-checked={on} className={on ? "md-choice is-on" : "md-choice"} onClick={() => pick(level, value)}>
                          {easyLabel(items, level, value)}
                          {sameAsAi(level, value) && <em className="md-ai-tag is-ai">AI 추정</em>}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {hasSignal && !none && <p className="md-note-text md-signal-note">신호 색(적색·녹색·황색)에 따라 비율이 크게 달라집니다. 영상에서 확실하지 않다면 실제 신호를 떠올려서 골라 주시기 바랍니다.</p>}

        {resolved && (
          <p className="md-base">
            이런 사고의 기본 책임은 <strong>내 차 {resolved.base_me}% : 상대 차 {resolved.base_other}%</strong>입니다.
          </p>
        )}
        {resolved && (
          <p className="md-official">
            손해보험협회 과실비율 인정기준의 표기: {resolved.place} · {resolved.feature} · 내 차 {resolved.my_progress} / 상대 차 {resolved.other_progress}
          </p>
        )}

        <label className={none ? "md-option md-none is-on" : "md-option md-none"}>
          <input type="checkbox" checked={none} onChange={(e) => setNone(e.target.checked)} />
          <span className="md-check" aria-hidden="true" />
          맞는 사고 유형이 없습니다 (과실 비율 없이 상황 설명만 보겠습니다)
        </label>
      </div>

      <footer className="md-foot md-foot-row">
        <button type="button" className="md-btn" disabled={!ready} onClick={() => onChoose(resolved)}>
          {none ? "결과 보기" : "다음으로"}
          <span aria-hidden="true">→</span>
        </button>
      </footer>
    </ModalShell>
  );
}
