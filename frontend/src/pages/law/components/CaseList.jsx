import { useState } from "react";
import CaseDetails from "./CaseDetails";

// selectedExtra: 좁은 화면에서 선택한 카드 바로 아래에 끼워 넣을 내용
// 상세 보기는 선택한 판례에서만 열 수 있고, 선택이 바뀌거나 해제되면 항상 접힘
export default function CaseList({ cases, selectedId, onToggle, selectedExtra, ref }) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [prevSelectedId, setPrevSelectedId] = useState(selectedId);
  if (prevSelectedId !== selectedId) {
    // 다른 판례를 고르거나 해제하면 이전 상세는 접고, 새 판례는 버튼만 보여 줌 (바로 펼치지 않음)
    setPrevSelectedId(selectedId);
    setDetailsOpen(false);
  }

  return (
    <section className="law-case-list" aria-label="유사 판례 목록" ref={ref}>
      {cases.map((item, index) => {
        const selected = item.id === selectedId;
        return [
          <CaseCard
            key={item.id}
            item={item}
            index={index}
            selected={selected}
            expanded={selected && detailsOpen}
            onToggle={() => onToggle(item.id)}
            onToggleDetails={() => setDetailsOpen((open) => !open)}
          />,
          selected && selectedExtra && (
            <div key={`${item.id}-extra`} className="law-inline-summary">
              {selectedExtra}
            </div>
          ),
        ];
      })}
    </section>
  );
}

// 판례 카드 1개: 한 줄에 법원 이름 + 핵심 수치 2개 + "상세 보기" 버튼
// 카드 아무 곳이나 누르면 선택, 선택된 카드를 한 번 더 누르면 해제 (on/off)
// "상세 보기" 버튼은 선택한 카드에만 나타나고(자리는 늘 비워 둬 숫자가 밀리지 않음), 누르면 펼치기만
function CaseCard({ item, index, selected, expanded, onToggle, onToggleDetails }) {
  const [mine, other] = item.ratio.split(":").map((v) => v.trim());
  const inputId = `law-case-${item.id}`;

  return (
    <article
      className={`law-case${selected ? " is-selected" : ""}${expanded ? " is-expanded" : ""}`}
      data-case-id={item.id}
      onClick={(e) => {
        // 법원 이름(label)을 누르면 숨은 라디오가 한 번 더 클릭되므로, 그쪽(아래 input onClick)에서만 처리
        if (e.target.closest("label, input")) return;
        onToggle();
      }}
    >
      <div className="law-case-row">
        <span className="law-case-number">{index + 1}</span>

        {/* 화면에는 안 보이는 선택 버튼: 키보드(Tab·Space)로도 고를 수 있게 */}
        <input
          id={inputId}
          className="law-sr-only"
          type="radio"
          name="similar-case"
          value={item.id}
          checked={selected}
          onClick={(e) => {
            e.stopPropagation();
            onToggle();
          }}
          onChange={() => {}} // 선택 상태는 위 onClick이 바꿈
        />
        <label className="law-court" htmlFor={inputId}>
          <strong>{item.court}</strong>
          <small>{item.date}</small>
        </label>

        {/* 핵심 수치: 작은 라벨 위 · 숫자 아래로 묶음 (두 숫자는 같은 크기) */}
        <dl className="law-case-metrics">
          <div>
            <dt>유사도</dt>
            <dd className="law-stat-sim">{item.similarity}</dd>
          </div>
          <div>
            <dt>기준 과실</dt>
            <dd>
              <span className="law-stat-mine">{mine}</span>
              <span className="law-stat-sep"> : </span>
              <span className="law-stat-other">{other}</span>
            </dd>
          </div>
        </dl>

        <button
          type="button"
          className={`law-detail-button${selected ? "" : " is-hidden"}`}
          aria-expanded={expanded}
          onClick={(e) => {
            e.stopPropagation(); // 펼치기만 하고 선택은 바꾸지 않음
            onToggleDetails();
          }}
        >
          {expanded ? "접기" : "상세 보기"}
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="m4 6 4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      <CaseDetails item={item} open={expanded} />
    </article>
  );
}

// 판례 목록 아래 안내 한 줄: ⓘ 아이콘 + 옅은 회색 글씨 (상자 없음)
export function GuideCard({ content }) {
  return (
    <p className="law-guide">
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <circle cx="8" cy="8" r="6.6" fill="none" stroke="currentColor" strokeWidth="1.3" />
        <path d="M8 7.2v4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
        <circle cx="8" cy="4.9" r="0.9" fill="currentColor" />
      </svg>
      {content.text}
    </p>
  );
}
