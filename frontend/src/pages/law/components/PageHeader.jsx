// 화면 맨 위: 구간 제목(칩 · 큰 제목 · 설명) + 그 아래 "내 사고" 한 줄
export default function PageHeader({ section, myAccident }) {
  return (
    <>
      <SectionTitle {...section} />
      <MyAccidentLine content={myAccident} />
    </>
  );
}

// 구간 제목: 어두운 둥근 칩 + 굵은 제목 + 설명
function SectionTitle({ chip, title, desc }) {
  return (
    <div className="law-section-title">
      {chip && <span className="law-chip-dark">{chip}</span>}
      <h2>{title}</h2>
      {desc && <p>{desc}</p>}
    </div>
  );
}

// 제목 아래 "내 사고" 한 줄: 이 화면이 무엇과 비교하는지 맨 위에서 기준을 잡아 줌
// (상자 없이 라벨 │ 정황 · 정황 · 정황)
function MyAccidentLine({ content }) {
  return (
    <p className="law-my-accident">
      <span className="law-my-accident-label">{content.label}</span>
      <span className="law-my-accident-points">
        {content.points.map((point, i) => (
          <span key={point}>
            {i > 0 && (
              <span className="law-my-accident-sep" aria-hidden="true">
                {" · "}
              </span>
            )}
            {point}
          </span>
        ))}
      </span>
    </p>
  );
}
