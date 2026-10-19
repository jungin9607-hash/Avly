/* ---------- 영상이 없을 때 보여 주는 도로 배경 (실제 장면이 아니다) ---------- */

export default function TimelineScene({ id }) {
  return (
    <svg className="tl-scene" viewBox="0 0 320 180" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <defs>
        <linearGradient id={`sky-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--bg)" />
          <stop offset="1" stopColor="var(--tl-scene-sky-bottom)" />
        </linearGradient>
      </defs>
      <rect width="320" height="72" fill={`url(#sky-${id})`} />
      <rect y="70" width="320" height="110" fill="var(--panel)" />
      <polygon points="146,70 174,70 330,180 -10,180" fill="var(--tl-scene-sky-bottom)" />
      <path d="M151 70 L40 180 M169 70 L280 180" stroke="#b8b8c4" strokeWidth="1.5" opacity="0.55" />
      <path d="M160 70 L160 180" stroke="#e2b25a" strokeWidth="1.5" opacity="0.7" />
      <path d="M155 70 L100 180 M165 70 L220 180" stroke="#fff" strokeWidth="1.2" strokeDasharray="7 9" opacity="0.35" />
    </svg>
  );
}
