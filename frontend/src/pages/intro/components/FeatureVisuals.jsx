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

// 블랙박스 화면 + 충돌 전후 타임라인 (빛나는 선으로 그린 HUD 화면: 차량 인식 박스)
function CamVisual() {
  return (
    <svg className="si-visual-cam" viewBox="0 0 200 132">
      <rect className="si-hud-frame" x="20" y="6" width="160" height="92" rx="6" />
      <path className="si-hud-dim" d="M24 30h152" />
      <path className="si-hud-line" d="M90 30 52 98M110 30l38 68" />
      <path className="si-hud-dim si-hud-dash" d="M100 34v62" />
      <rect className="si-hud-line" x="114" y="54" width="22" height="13" rx="3" />
      <path className="si-hud-alert" d="M108 54v-6h7M142 54v-6h-7M108 68v6h7M142 68v6h-7" />
      <text className="si-hud-alert-text" x="142" y="45" fontSize="7" textAnchor="end">
        차량 인식
      </text>
      <circle className="si-hud-alert-dot" cx="31" cy="16" r="2.5" />
      <text className="si-hud-text" x="37" y="19" fontSize="7" fontWeight="700">
        REC
      </text>
      <text className="si-hud-text" x="170" y="19" fontSize="7" textAnchor="end">
        00:12
      </text>
      <path className="si-hud-dim" d="M28 116h144" />
      {TIMELINE.map(([x, t]) => (
        <g key={t}>
          <circle className="si-hud-node" cx={x} cy="116" r="3.5" />
          <text className="si-hud-muted" x={x} y="130" fontSize="8" textAnchor="middle">
            {t}
          </text>
        </g>
      ))}
      <circle className="si-hud-alert-dot" cx="168" cy="116" r="4.5" />
      <text className="si-hud-alert-text" x="168" y="130" fontSize="8" fontWeight="700" textAnchor="middle">
        충돌
      </text>
    </svg>
  );
}

// 예상 과실비율: 빛나는 숫자 · 막대 게이지(아래 눈금)
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
