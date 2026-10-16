export default function TimelineControls({ active, last, onSelect }) {
  return (
    <div className="tl-counter">
      <button type="button" aria-label="이전 시점" onClick={() => onSelect(active - 1)} disabled={active === 0}>
        ←
      </button>
      <button type="button" aria-label="다음 시점" onClick={() => onSelect(active + 1)} disabled={active === last}>
        →
      </button>
    </div>
  );
}
