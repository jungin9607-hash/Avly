import { Link } from "react-router-dom";
import { IconArrowRight, IconDownload, IconShare } from "./icons";

// "사고 타임라인 바로가기": 유사 판례 화면의 "분석 결과 바로가기"와 같은 디자인 · 같은 위치(창 오른쪽 아래 구석)
// visible: 증거 구간까지 스크롤했을 때만 나타남 (보이지 않을 때는 Tab·화면 낭독기에서도 빠짐)
export function TimelineLink({ content, visible = true }) {
  return (
    <Link
      to={content.to}
      className={`ar-timeline-link${visible ? " is-visible" : ""}`}
      aria-hidden={!visible}
      tabIndex={visible ? undefined : -1}
    >
      <strong>{content.label}</strong>
      <IconArrowRight />
    </Link>
  );
}

// 증거 화면 맨 아래 오른쪽: 같은 크기 버튼 한 쌍
// 왼쪽 "분석 결과 저장"(밝은 채움, 주 버튼) | 오른쪽 "공유하기"(투명 + 옅은 흰 테두리, 보조 버튼)
// expiresText: "오후 3:20" 같은, 결과가 자동으로 삭제되는 시각 (없으면 안내를 생략)
export default function ReportActions({ content, onShare, onSave, onErase, expiresText }) {
  return (
    <aside className="ar-actions-panel" aria-label={content.title}>
      <div className="ar-actions">
        <button type="button" className="ar-text-action ar-text-action-pdf" onClick={onSave}>
          {content.pdf}
          <IconDownload />
        </button>
        <button type="button" className="ar-text-action ar-text-action-share" onClick={onShare}>
          {content.share}
          <IconShare />
        </button>
      </div>
      <div className="ar-erase">
        {expiresText && <p>이 결과는 {expiresText}에 자동으로 삭제돼요.</p>}
        <button type="button" className="ar-erase-button" onClick={onErase}>
          {content.erase}
        </button>
      </div>
    </aside>
  );
}
