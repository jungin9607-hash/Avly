import { Link } from "react-router-dom";
import { IconArrowRight, IconDownload, IconShare } from "./icons";

// "사고 타임라인 바로가기": 증거 제목 줄 오른쪽 끝, 블루로 강조한 다음 단계 링크
export function TimelineLink({ content }) {
  return (
    <Link to={content.to} className="ar-timeline-link">
      <span className="ar-timeline-link-text">
        <strong>{content.label}</strong>
      </span>
      <IconArrowRight />
    </Link>
  );
}

// 증거 화면 맨 아래 오른쪽: 다운로드 버튼과 공유하기
export default function ReportActions({ content, onShare }) {
  return (
    <aside className="ar-actions-panel" aria-label={content.title}>
      <div className="ar-actions">
        <button type="button" className="ar-text-action ar-text-action-share" onClick={onShare}>
          {content.share}
          <IconShare />
        </button>
        <button type="button" className="ar-text-action ar-text-action-pdf" onClick={() => window.print()}>
          {content.pdf}
          <IconDownload />
        </button>
      </div>
    </aside>
  );
}
