import { useLayoutEffect, useState } from "react";
import { CheckIcon } from "./CaseDetails";

// 오른쪽 열: 선택한 판례 카드와 같은 높이로 내려가 그 옆에 붙어 있음
// listRef: 판례 목록, 카드마다 data-case-id 가 있음
export default function SummaryAside({ listRef, selectedId, children }) {
  const [offset, setOffset] = useState(0);

  useLayoutEffect(() => {
    const list = listRef.current;
    if (!list || !selectedId) return;

    const measure = () => {
      const card = list.querySelector(`[data-case-id="${selectedId}"]`);
      if (!card) return;
      setOffset(card.getBoundingClientRect().top - list.getBoundingClientRect().top);
    };
    measure();

    // "상세 보기"로 카드가 펼쳐지거나 화면 폭이 바뀌어 위치가 달라져도 따라감
    const observer = new ResizeObserver(measure);
    observer.observe(list);
    return () => observer.disconnect();
  }, [listRef, selectedId]);

  if (!selectedId) return null;

  return (
    <aside className="law-analysis" style={{ "--law-follow-y": `${offset}px` }}>
      {children}
    </aside>
  );
}

// 선택한 판례가 내 사고와 비슷한 이유 (판례를 바꾸면 내용도 바뀜)
export function SummaryCard({ content, caseItem }) {
  return (
    <section className="law-summary-card" aria-label={content.title}>
      <p className="law-summary-kicker">{content.title}</p>

      {/* 어느 판례인지는 바로 옆 선택한 카드로 알 수 있어 법원 이름은 생략.
          key가 바뀌면 다시 그려지며 살짝 반짝여 갱신된 걸 알려 줌 */}
      <ul className="law-match-factors" key={caseItem.id}>
        {caseItem.factors.map((factor) => (
          <li key={factor}>
            <CheckIcon />
            {factor}
          </li>
        ))}
      </ul>
    </section>
  );
}
