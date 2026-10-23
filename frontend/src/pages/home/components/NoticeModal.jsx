import ModalShell from "./ModalShell";

// 안내 팝업: 제목과 설명, 버튼 한두 개 (지원하지 않는 사고, 실패 등)
export default function NoticeModal({ title, desc, children, primary, secondary, onClose, sticky }) {
  return (
    <ModalShell title={title} desc={desc} onClose={onClose} sticky={sticky}>
      {children && <div className="md-body">{children}</div>}
      <footer className="md-foot md-foot-row">
        {primary && (
          <button type="button" className="md-btn" onClick={primary.onClick}>
            {primary.label}
          </button>
        )}
        {secondary && (
          <button type="button" className="md-btn-ghost" onClick={secondary.onClick}>
            {secondary.label}
          </button>
        )}
      </footer>
    </ModalShell>
  );
}
