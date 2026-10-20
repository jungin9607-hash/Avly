import { STAGE_LABELS, stageIndex } from "../../../api/adapters";
import ModalShell from "./ModalShell";

// 서버가 일하는 동안 보여 주는 진행 팝업.
//   phase  uploading(영상 올리는 중, progress 0~1) | analyzing(분석 중, stage) | finalizing(결과 계산 중)
export default function AnalysisProgressModal({ phase, progress = 0, stage, onClose }) {
  const titles = { uploading: "영상을 올리는 중", analyzing: "영상 분석 중", finalizing: "결과를 계산하는 중" };
  const current = phase === "analyzing" ? stageIndex(stage) : -1;
  const percent = Math.round(progress * 100);

  return (
    <ModalShell
      title={titles[phase]}
      desc={phase === "analyzing" ? "번호판과 사람을 가린 뒤 사고 장면과 차량 움직임을 분석해요. 영상 길이에 따라 몇 분 걸릴 수 있어요." : undefined}
      progress={[2, 4]}
      onClose={onClose}
      sticky
    >
      <div className="md-analysis" role="status" aria-live="polite">
        <span className="md-analysis-spinner" aria-hidden="true" />
        {phase === "uploading" && (
          <>
            <p>{percent}%</p>
            <div className="md-bar" aria-hidden="true">
              <span style={{ width: `${percent}%` }} />
            </div>
          </>
        )}
        {phase === "analyzing" && (
          <ol className="md-stages">
            {STAGE_LABELS.map((item, index) => (
              <li key={item.id} className={index < current ? "is-done" : index === current ? "is-active" : ""}>
                <span aria-hidden="true">{index < current ? "✓" : index + 1}</span>
                {item.label}
              </li>
            ))}
          </ol>
        )}
        {phase === "finalizing" && <p>가감요소를 반영해서 과실 비율을 계산하고 있어요.</p>}
        {phase === "analyzing" && <p className="md-hint">창을 닫아도 분석은 계속돼요. 분석이 끝나면 상단 메뉴의 &lsquo;분석 결과&rsquo;에서 볼 수 있어요.</p>}
      </div>
    </ModalShell>
  );
}
