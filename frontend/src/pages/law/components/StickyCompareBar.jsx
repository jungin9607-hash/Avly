// 판례 목록 아래 가운데의 "내 사고와 비교하기" 버튼 하나 (상세 보기로 길어지면 화면 아래에 붙어 따라옴)
// 판례를 아직 고르지 않았으면(caseItem 없음) 비활성 + "비교할 판례를 선택해 주세요"로 이유를 알려 줌
// 고르면(is-active) 버튼이 한 번 톡 커지며 은은하게 빛남
export default function StickyCompareBar({ content, caseItem, onOpen }) {
  return (
    <aside className={`law-sticky${caseItem ? " is-active" : ""}`} aria-label="선택한 판례 비교 바로가기">
      {/* 판례를 고르거나 바꿀 때마다 key가 바뀌어 버튼이 다시 한 번 빛남 */}
      <button
        key={`button-${caseItem?.id ?? "none"}`}
        type="button"
        className="law-sticky-button"
        onClick={onOpen}
        disabled={!caseItem}
      >
        {caseItem ? content.button : content.emptyLabel}
        {caseItem && <span aria-hidden="true">→</span>}
      </button>
    </aside>
  );
}
