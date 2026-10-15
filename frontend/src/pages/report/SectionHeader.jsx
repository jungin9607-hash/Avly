// 구간 제목: 왼쪽 아이콘 상자 + 제목 + 한 줄 안내 ("왜 20:80으로 분석됐나요?", "영상으로 확인한 증거")
export default function SectionHeader({ icon, title, desc }) {
  return (
    <header className="ar-icon-head">
      <span className="ar-icon-head-icon" aria-hidden="true">
        {icon}
      </span>
      <div>
        <h2>{title}</h2>
        {desc && <p>{desc}</p>}
      </div>
    </header>
  );
}

// 체크리스트 아이콘 (과실 조정 요인)
export const ChecklistIcon = () => (
  <svg viewBox="0 0 24 24">
    <rect x="3.5" y="3.5" width="17" height="17" rx="3" />
    <path d="M7.5 8.5h5M7.5 12h3M7.5 15.5h4M13.5 14l2 2 3.5-4" />
  </svg>
);

// 방패 + 돋보기 아이콘 (영상 증거)
export const ShieldSearchIcon = () => (
  <svg viewBox="0 0 24 24">
    <path d="M12 3 5 6v5c0 4.5 3 8.5 7 10 4-1.5 7-5.5 7-10V6z" />
    <circle cx="11.5" cy="11.5" r="2.8" />
    <path d="m13.6 13.6 2 2" />
  </svg>
);
