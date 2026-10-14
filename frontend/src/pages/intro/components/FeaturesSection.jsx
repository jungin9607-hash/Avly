import { useNavigate } from "react-router-dom";
import { VISUALS } from "./FeatureVisuals";

// 핵심 기능 3가지: 도로 화면에서 이어지는 진한 네이비 배경 위 흰 카드 + 아래 가운데 시작 버튼
export default function FeaturesSection({ content, cta }) {
  return (
    <section className="si-features">
      <div className="si-features-inner">
        <h2>
          <strong>{content.title}</strong>
        </h2>

        <div className="si-cards">
          {content.cards.map(({ id, ...card }) => (
            <FeatureCard key={id} {...card} />
          ))}
        </div>

        <CtaBar content={cta} />
      </div>
    </section>
  );
}

function FeatureCard({ title, visual, desc }) {
  const Visual = VISUALS[visual];

  return (
    <article className="si-card">
      <h3>{title}</h3>
      <div className="si-card-visual" aria-hidden="true">
        {Visual && <Visual />}
      </div>
      {/* 가운데 정렬 문단, 줄바꿈은 박스 폭에 맞춰 자동 (CSS text-wrap: balance) */}
      <p className="si-card-desc">
        <RichText parts={desc} />
      </p>
    </article>
  );
}

// 기능 소개를 다 본 뒤 바로 시작할 수 있게: 카드 아래 가운데 버튼만
function CtaBar({ content }) {
  const navigate = useNavigate();

  return (
    <div className="si-cta-bar">
      <div className="si-cta-buttons">
        {content.buttons.map((btn) => (
          <button key={btn.to} className={`si-btn si-btn-${btn.variant}`} onClick={() => navigate(btn.to)}>
            {btn.label}
            {btn.arrow && (
              <span className="si-btn-arrow" aria-hidden="true">
                ›
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

// 문장 조각 배열을 그림: 문자열은 그대로, { em: "..." }는 핵심 단어 표시, { br: true }는 줄바꿈
function RichText({ parts }) {
  return parts.map((part, i) => {
    if (typeof part === "string") return part;
    if (part.br) return <br key={i} />;
    return (
      <em key={i} className="si-em">
        {part.em}
      </em>
    );
  });
}
