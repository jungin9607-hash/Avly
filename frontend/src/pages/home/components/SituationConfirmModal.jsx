import { useState } from "react";
import { LEVEL_LABEL, cascade, easyLabel, easyOf, normalizeSelection, resolveOption, selectionFrom } from "../../../api/adapters";
import ModalShell from "./ModalShell";

const LEVELS = ["place", "feature", "my_progress", "other_progress"];

// 3단계: AI 가 파악한 사고 상황을 사용자가 확인하고 고친다.
//   장소 → 사고 유형 → 내 차의 움직임 → 상대 차의 움직임 순서로 고르며, 앞 항목을 바꾸면 뒤 항목의 보기가 좁혀진다.
//   AI 가 확신한 후보가 있으면 미리 골라 둔다. 참고 후보만 있거나 후보가 없으면 비워 둔다.
//   맞는 유형이 없다고 답할 수도 있다 (그러면 과실 비율 없이 결과를 보여 준다).
export default function SituationConfirmModal({ situation, items, onChoose, onClose }) {
  const candidates = situation?.candidates ?? [];
  const preset = situation?.default_index != null ? candidates[situation.default_index] : null;
  const [selection, setSelection] = useState(() => selectionFrom(preset));
  const [none, setNone] = useState(false);

  if (!items) {
    return (
      <ModalShell title="AI가 분석한 사고 상황이 맞나요?" progress={[3, 4]} onClose={onClose} sticky>
        <div className="md-analysis" role="status">
          <span className="md-analysis-spinner" aria-hidden="true" />
          <p>선택지를 불러오는 중이에요.</p>
        </div>
      </ModalShell>
    );
  }

  const options = cascade(items, selection);
  const resolved = none ? null : resolveOption(items, selection);
  const ready = none || resolved;
  const pick = (level, value) => setSelection((current) => normalizeSelection(items, { ...current, [level]: value }));
  const otherCandidates = candidates.filter((c) => !(preset && c.accident_type_id === preset.accident_type_id && c.role === preset.role));

  return (
    <ModalShell
      title="AI가 분석한 사고 상황이 맞나요?"
      desc="영상에서 파악한 내용이에요. 다르면 아래에서 직접 고쳐 주세요."
      progress={[3, 4]}
      onClose={onClose}
      sticky
    >
      <div className="md-body">
        {situation?.summary && (
          <section className="md-situation" aria-label="AI가 본 사고 상황">
            <p className="md-situation-label">AI가 본 상황</p>
            <p>{situation.summary}</p>
          </section>
        )}
        {situation?.needs_check?.length > 0 && (
          <ul className="md-note">
            {situation.needs_check.map((text) => (
              <li key={text}>{text}</li>
            ))}
          </ul>
        )}

        {!preset && candidates.length > 0 && <p className="md-hint">AI가 확신하지 못했어요. 아래 후보를 눌러 보거나 직접 골라 주세요.</p>}
        {otherCandidates.length > 0 && (
          <div className="md-chips" aria-label={preset ? "다른 후보" : "참고 후보"}>
            {otherCandidates.map((c) => (
              <button
                key={`${c.accident_type_id}-${c.role}`}
                type="button"
                className="md-chip"
                onClick={() => {
                  setNone(false);
                  setSelection(selectionFrom(c));
                }}
              >
                {easyOf(c, "feature")} · 내 차 {easyOf(c, "my_progress")}
              </button>
            ))}
          </div>
        )}

        <div className="md-fields">
          {LEVELS.map((level, index) => (
            <label key={level} className="md-field">
              <span>
                <b>{index + 1}</b>
                {LEVEL_LABEL[level]}
              </span>
              <select
                className="md-select"
                value={selection[level]}
                disabled={none || (index > 0 && !selection[LEVELS[index - 1]])}
                onChange={(e) => pick(level, e.target.value)}
              >
                <option value="">선택해 주세요</option>
                {options[level].map((value) => (
                  <option key={value} value={value}>
                    {easyLabel(items, level, value)}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>

        {resolved && (
          <p className="md-base">
            이런 사고의 기본 책임은 <strong>내 차 {resolved.base_me}% : 상대 차 {resolved.base_other}%</strong>예요.
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
          맞는 사고 유형이 없어요 (과실 비율 없이 상황 설명만 볼게요)
        </label>
      </div>

      <footer className="md-foot md-foot-row">
        <button type="button" className="md-btn" disabled={!ready} onClick={() => onChoose(resolved)}>
          {none ? "결과 보기" : "맞아요, 다음으로"}
          <span aria-hidden="true">→</span>
        </button>
      </footer>
    </ModalShell>
  );
}
