// "에블리가 하는 일" 카드 속 그림 3개 (introContent.js의 visual 값으로 고름)
export const VISUALS = {
  cam: CamVisual,
  ratio: RatioVisual,
  doc: DocVisual,
};

const TIMELINE = [
  [36, "-5초"],
  [82, "-3초"],
  [128, "-1초"],
];

// 블랙박스 화면 + 충돌 전후 타임라인
function CamVisual() {
  return (
    <svg className="si-visual-cam" viewBox="0 0 200 132">
      <rect x="20" y="6" width="160" height="92" rx="8" fill="#22242c" />
      <path d="M92 26 L108 26 L156 98 L44 98 Z" fill="#3a3d48" />
      <path d="M99.2 34h1.6v8h-1.6zM98.8 50h2.4v12h-2.4zM98.2 72h3.6v18h-3.6z" fill="#f2cc47" />
      <rect x="112" y="52" width="26" height="16" rx="3" fill="#5a5f70" />
      <rect x="114" y="62" width="5" height="3" rx="1" fill="#ff5a4a" />
      <rect x="131" y="62" width="5" height="3" rx="1" fill="#ff5a4a" />
      <circle cx="32" cy="18" r="3" fill="#ff5a4a" />
      <text x="39" y="21" fontSize="8" fontWeight="700" fill="#fff">REC</text>
      <line x1="28" y1="116" x2="172" y2="116" stroke="#cfd0d6" strokeWidth="2" />
      {TIMELINE.map(([x, t]) => (
        <g key={t}>
          <circle cx={x} cy="116" r="4" fill="#fff" stroke="#9a9ca6" strokeWidth="2" />
          <text x={x} y="130" fontSize="8" textAnchor="middle" fill="#7a7c86">
            {t}
          </text>
        </g>
      ))}
      <circle cx="168" cy="116" r="5" fill="#ff5a4a" />
      <text x="168" y="130" fontSize="8" fontWeight="700" textAnchor="middle" fill="#e2463a">
        충돌
      </text>
    </svg>
  );
}

// 예상 과실비율 카드
function RatioVisual({ mine = 20, other = 80 }) {
  return (
    <div className="si-mini si-ratio">
      <span className="si-ratio-label">내 차 : 상대 차 (예시)</span>
      <strong className="si-ratio-value">
        {mine} : {other}
      </strong>
      <div className="si-ratio-bar">
        <span style={{ width: `${mine}%` }} />
        <span style={{ width: `${other}%` }} />
      </div>
      <span className="si-ratio-source">과실 인정 기준 · 출처 표시</span>
    </div>
  );
}

const CHECKS = ["비슷한 판례 검색", "공통점·차이점 비교", "모든 근거에 출처"];

// 판례 문서 + 체크 목록
function DocVisual() {
  return (
    <div className="si-mini si-doc">
      <span className="si-doc-tag">판례</span>
      <span className="si-doc-line" />
      <span className="si-doc-line short" />
      <ul className="si-check">
        {CHECKS.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
