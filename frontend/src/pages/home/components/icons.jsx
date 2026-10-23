/* 업로드 화면 아이콘 (선 아이콘, currentColor) */
const Svg = ({ children, size = 20, strokeWidth = 1.8 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={strokeWidth}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);
export const IconUpload = () => (
  <Svg size={30}>
    <path d="M7 18a4.5 4.5 0 0 1-.6-8.96A6 6 0 0 1 18 8.5a4 4 0 0 1-.5 9.5" />
    <path d="M12 12v8M8.5 15.5 12 12l3.5 3.5" />
  </Svg>
);
export const IconPlus = () => (
  <Svg size={18}>
    <circle cx="12" cy="12" r="10" fill="currentColor" stroke="none" />
    <path d="M12 7.5v9M7.5 12h9" stroke="var(--color-white)" strokeWidth="2.2" />
  </Svg>
);
export const IconShield = () => (
  <Svg size={18}>
    <path d="M12 3 5 6v5c0 4.5 3 8.5 7 10 4-1.5 7-5.5 7-10V6z" />
    <path d="m9.5 12 2 2 3.5-4" />
  </Svg>
);

/* 영상 가이드 카드 아이콘: 블랙박스 · 스톱워치 · 음소거 */
export const IconDashcam = () => (
  <Svg size={48} strokeWidth={1.3}>
    <path d="M6.8 2.6h11.1c0 1.9-1.6 3.2-3.4 3.2h-4.3C8.4 5.8 6.8 4.5 6.8 2.6z" />
    <path d="M11.4 5.8v2.1M13.3 5.8v2.1" />
    <rect x="8.6" y="7.9" width="7.2" height="1.6" rx="0.3" />
    <rect x="2.4" y="9.5" width="19.2" height="11.9" rx="2.6" />
    <circle cx="12" cy="15.45" r="3.45" />
    <circle cx="12" cy="15.45" r="1.8" />
  </Svg>
);
export const IconStopwatch = () => (
  <Svg size={48} strokeWidth={1.3}>
    {/* 동그라미 본체가 상자 가운데에 오도록 옮긴다 (속도선은 왼쪽으로 나감) */}
    <g transform="translate(-2 -0.75)">
      <path d="M9 7.26A8 8 0 1 1 9.5 20.12" />
      <path d="M14 5.5V3M11.5 3h5" />
      <path d="m10.8 13.8 2.4 2.4 4.8-4.8" />
      <path d="M3 10.5h4M2.3 13.5h4.2M3 16.5h4" />
    </g>
  </Svg>
);
export const IconMute = () => (
  <Svg size={48} strokeWidth={1.13}>
    {/* 시계 아이콘과 같은 크기로 1.15배 키우고(선 두께는 그만큼 줄여 1.3으로 보이게), 스피커 쪽이 무거워 보여서 오른쪽으로 조금 옮긴다 */}
    <g transform="translate(12 12) scale(1.15) translate(-11.5 -12)">
      <path d="M3 9h4l5-4.5v15L7 15H3z" />
      <path d="m16 9.5 5 5M21 9.5l-5 5" />
    </g>
  </Svg>
);
