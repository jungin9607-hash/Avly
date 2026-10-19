import { Link } from "react-router-dom";

// 판례 목록 아래 가운데의 "내 사고와 비교하기" 버튼 (상세 보기로 길어지면 화면 아래에 붙어 따라옴)
// 판례를 아직 고르지 않았으면(caseItem 없음) 비활성 + "비교할 판례를 선택해 주세요"로 이유를 알려 줌
// 판례 선택 후 마우스를 올리면 intro 주 버튼처럼 빛 고리가 퍼짐
// 판례를 고르면 오른쪽에 "분석 결과 바로가기"(보조 버튼)가 나타남
export default function StickyCompareBar({ content, caseItem, onOpen, resultTo }) {
  return (
    <aside className={`law-sticky${caseItem ? " is-active" : ""}`} aria-label="선택한 판례 비교 바로가기">
      <button
        type="button"
        className="law-sticky-button"
        onClick={onOpen}
        disabled={!caseItem}
      >
        {caseItem ? content.button : content.emptyLabel}
        {caseItem && <span aria-hidden="true">→</span>}
      </button>

      {caseItem && (
        <Link to={resultTo} className="law-result-link">
          <strong>{content.result.label}</strong>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </Link>
      )}
    </aside>
  );
}
