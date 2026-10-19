/* 업로드 화면 아이콘 (선 아이콘, currentColor) */
const Svg = ({ children, size = 20 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
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
    <circle cx="12" cy="12" r="9" />
    <path d="M12 8v8M8 12h8" />
  </Svg>
);
export const IconShield = () => (
  <Svg size={18}>
    <path d="M12 3 5 6v5c0 4.5 3 8.5 7 10 4-1.5 7-5.5 7-10V6z" />
    <path d="m9.5 12 2 2 3.5-4" />
  </Svg>
);
