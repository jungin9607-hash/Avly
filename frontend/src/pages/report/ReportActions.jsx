import { Link } from "react-router-dom";
import { IconArrowRight, IconDownload, IconScale, IconShare } from "./icons";

// 증거 오른쪽 패널: PDF 다운로드 · 공유하기 + "이 판단과 비슷한 판례 보기" (스크롤해도 따라옴)
export default function ReportActions({ content, onShare }) {
  return (
    <aside className="ar-actions-panel" aria-label={content.title}>
      <div className="ar-actions-card">
        <h3>{content.title}</h3>
        <p>{content.desc}</p>
        <div className="ar-actions">
          <button type="button" className="ar-btn ar-btn-solid" onClick={() => window.print()}>
            <IconDownload />
            {content.pdf}
          </button>
          <button type="button" className="ar-btn ar-btn-line" onClick={onShare}>
            <IconShare />
            {content.share}
          </button>
        </div>
      </div>

      <Link to={content.law.to} className="ar-law-link">
        <span className="ar-law-link-icon">
          <IconScale />
        </span>
        <span className="ar-law-link-text">
          <strong>{content.law.label}</strong>
          <small>{content.law.desc}</small>
        </span>
        <IconArrowRight />
      </Link>
    </aside>
  );
}
