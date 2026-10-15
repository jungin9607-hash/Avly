// 분석 결과 화면에서 쓰는 작은 선 아이콘
const Svg = ({ children, size = 18 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.9"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);

export const IconTarget = () => (
  <Svg size={16}>
    <circle cx="12" cy="12" r="8" />
    <circle cx="12" cy="12" r="3" />
    <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
  </Svg>
);
export const IconGavel = () => (
  <Svg size={16}>
    <path d="m14 4 6 6M11 7l6 6M12.5 5.5l-6 6M18.5 11.5l-6 6M9 14l-6 6M3 21h9" />
  </Svg>
);
export const IconDownload = () => (
  <Svg size={18}>
    <path d="M12 4v11M7 10l5 5 5-5M5 20h14" />
  </Svg>
);
export const IconShare = () => (
  <Svg size={18}>
    <circle cx="18" cy="5" r="2.5" />
    <circle cx="6" cy="12" r="2.5" />
    <circle cx="18" cy="19" r="2.5" />
    <path d="m8.2 10.8 7.6-4.4M8.2 13.2l7.6 4.4" />
  </Svg>
);
// 저울 (판례)
export const IconScale = () => (
  <Svg size={22}>
    <path d="M12 4v16M7 20h10M5 7h14M5 7l-3 6a3 3 0 0 0 6 0zM19 7l-3 6a3 3 0 0 0 6 0z" />
  </Svg>
);
export const IconArrowRight = () => (
  <Svg size={18}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </Svg>
);
