import ModalShell from "./ModalShell";

export default function SituationConfirmModal({ onConfirm, onBack, onClose }) {
  return (
    <ModalShell
      title="AI가 분석한 사고 상황이 맞나요?"
      desc="영상에서 파악한 사고 유형과 주요 상황을 확인해 주세요."
      progress={[5, 5]}
      onClose={onClose}
    >
      <div className="md-body">
        <section className="md-situation" aria-label="AI가 분석한 사고 상황">
          <p className="md-situation-label">사고 유형</p>
          <h3>차선 변경 중 접촉 사고</h3>
          <p>
            상대 차량이 방향지시등을 켜지 않고 진입했고, 내 차량은 정상 차로로 주행 중 충돌한 상황으로 분석했어요.
          </p>
        </section>
      </div>
      <footer className="md-foot md-confirm-foot">
        <button type="button" className="md-btn" onClick={onConfirm}>
          맞아요, 분석 결과 보기
          <span aria-hidden="true">→</span>
        </button>
        <button type="button" className="md-btn-ghost" onClick={onBack}>
          아니요, 다시 확인할게요
        </button>
      </footer>
    </ModalShell>
  );
}
