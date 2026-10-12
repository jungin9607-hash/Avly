import { useState } from "react";
import Icon from "../../../components/ui/Icon";
import { ReanalyzeOption } from "../ModalParts";
import { REANALYZE_OPTIONS } from "../constants";

function ReanalysisStage({ onBack, onSubmit }) {
  const [reason, setReason] = useState(REANALYZE_OPTIONS[0].value);

  return (
    <div className="modal-stage">
      <div>
        <h3>AI 재분석 요청 사유 선택</h3>
        <p className="modal-description">실제 사고 상황과 다른 항목을 선택해 주세요.</p>
      </div>

      <div className="reanalyze-options">
        {REANALYZE_OPTIONS.map((option) => (
          <ReanalyzeOption
            key={option.value}
            checked={reason === option.value}
            onChange={() => setReason(option.value)}
            title={option.title}
            description={option.description}
          />
        ))}
      </div>

      <div className="reanalyze-buttons">
        <button type="button" className="back-button" onClick={onBack}>
          ← 이전으로 돌아가기
        </button>

        <button type="button" className="modal-primary-button" onClick={onSubmit}>
          <Icon name="auto_fix_high" />
          재분석
        </button>
      </div>
    </div>
  );
}

export default ReanalysisStage;
