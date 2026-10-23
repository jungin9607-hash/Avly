import { useId, useState } from "react";

// "○○ 보기 ⌄" 파란 글씨 버튼 + 누르면 아래로 부드럽게 펼쳐지는 내용
// (법적 근거 자세히 보기, 분석 방법 보기 등에서 함께 씀)
export default function Disclosure({ label, openLabel, children }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  return (
    <>
      <button
        type="button"
        className="ar-more"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? openLabel : label}
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>
      {/* 높이를 0fr ↔ 1fr로 바꿔 부드럽게 펼침 */}
      <div id={panelId} className={open ? "ar-more-panel is-open" : "ar-more-panel"}>
        <div className="ar-more-clip">{children}</div>
      </div>
    </>
  );
}
