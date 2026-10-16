import Disclosure from "./Disclosure";
import { IconGavel, IconTarget } from "./icons";

const FOOT_ICONS = { target: IconTarget, gavel: IconGavel };

// 증거 카드: 위 장면 사진 | 아래 (제목 ……… 태그) → 설명 · 근거 한 줄 · 분석 방법 보기
// (좁은 화면에서는 왼쪽 사진 | 오른쪽 글)
export default function EvidenceCard({ item }) {
  const FootIcon = item.foot && FOOT_ICONS[item.foot.icon];
  return (
    <div className="ar-ev-row">
      {item.frame && <EvidenceFrame frame={item.frame} alt={item.title} />}
      <div className="ar-ev-text">
        <div className="ar-ev-head">
          <h3>{item.title}</h3>
          <span className={item.warn ? "ar-ev-tag warn" : "ar-ev-tag"}>{item.tag}</span>
        </div>
        <p>{item.body}</p>
        {item.foot && (
          <p className="ar-ev-foot">
            {FootIcon && <FootIcon />}
            <span>{item.foot.text}</span>
          </p>
        )}
        {item.method && (
          <Disclosure label="분석 방법 보기" openLabel="분석 방법 접기">
            <p className="ar-ev-method">{item.method}</p>
          </Disclosure>
        )}
      </div>
    </div>
  );
}

// 장면 사진 한 장 (+ 방향지시등 자리 표시)
// frame.src가 있으면 그 사진을, 없으면 사진이 준비될 때까지 앞차 뒷모습 그림을 보여 줌
function EvidenceFrame({ frame, alt }) {
  return (
    <figure className="ar-frame">
      {frame.src ? <img src={frame.src} alt={alt} /> : <CarRear />}
      {frame.mark && <span className="ar-frame-box" aria-hidden="true" />}
    </figure>
  );
}

// 블랙박스 프레임 자리: 앞차 뒷모습 (왼쪽 방향지시등 자리를 표시)
function CarRear() {
  return (
    <svg className="ar-car" viewBox="0 0 160 90" aria-hidden="true">
      <rect x="0" y="62" width="160" height="28" fill="#2a2a33" />
      <path d="M0 76 H160" stroke="#55555f" strokeWidth="1" strokeDasharray="10 8" />
      <path d="M44 30 Q48 16 62 14 H98 Q112 16 116 30 Z" fill="#3a3d48" />
      <path d="M52 28 Q55 19 64 18 H96 Q105 19 108 28 Z" fill="#1b1d24" />
      <rect x="36" y="30" width="88" height="30" rx="5" fill="#5b5f6c" />
      <rect x="40" y="36" width="16" height="7" rx="1.5" fill="#6b2a2a" />
      <rect x="104" y="36" width="16" height="7" rx="1.5" fill="#6b2a2a" />
      <rect x="68" y="46" width="24" height="7" rx="1" fill="#d9d9de" />
      <rect x="40" y="60" width="12" height="7" rx="2" fill="#16161b" />
      <rect x="108" y="60" width="12" height="7" rx="2" fill="#16161b" />
    </svg>
  );
}
