// 구간 제목: 작은 블루 머리말 + 큰 제목 + 한 줄 안내 ("왜 20:80으로 분석됐나요?", "영상으로 확인한 증거")
export default function SectionHeader({ kicker, title, desc }) {
  return (
    <header className="ar-icon-head">
      <div>
        {kicker && <p className="ar-section-kicker">{kicker}</p>}
        <h2>{title}</h2>
        {desc && <p>{desc}</p>}
      </div>
    </header>
  );
}
