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

// 증거 화면 맨 아래 오른쪽: "분석 결과 활용하기" 소제목 + PDF 다운로드 · 공유하기 밑줄 링크 (상자 없음)
export default function ReportActions({ content, onShare }) {
  return (
    <aside className="ar-actions-panel" aria-label={content.title}>
      <h3>{content.title}</h3>
      <div className="ar-actions">
        {/* 상자 없이 글자 왼쪽 · 아이콘 오른쪽 + 아래 흰 밑줄 */}
        <button type="button" className="ar-text-action" onClick={() => window.print()}>
          {content.pdf}
          <IconDownload />
        </button>
        <button type="button" className="ar-text-action" onClick={onShare}>
          {content.share}
          <IconShare />
        </button>
      </div>
    </aside>
  );
}
