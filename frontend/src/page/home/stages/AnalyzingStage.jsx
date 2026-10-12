import Icon from "../../../components/ui/Icon";
import { Milestone } from "../ModalParts";
import { STAGE } from "../constants";

const MILESTONES = [
  { text: "영상 디코딩 및 텔레메트리 추출", doneAt: 15 },
  { text: "충돌 전후 프레임 객체 인식", doneAt: 85 },
  { text: "과실비율 기준 및 판례 매칭", doneAt: 100 },
];

function AnalyzingStage({ stage, progress, onFastForward }) {
  const isRe = stage === STAGE.REANALYZING;

  return (
    <div className="modal-stage">
      <div className="analysis-heading">
        <span className="analyzing-badge">
          {isRe ? "답변 반영 AI 재분석 중" : "AI 비전 심층 추론 엔진 가동 중"}
        </span>

        <h3>
          {isRe
            ? "답변 내용을 반영해 사고 상황을 재분석하고 있습니다"
            : "에블리 AI가 영상을 정밀 분석하고 있습니다"}
        </h3>

        <p className="modal-description">
          {isRe
            ? "선택하신 답변을 영상 분석 및 과실 판단에 반영하고 있습니다."
            : "차량 객체와 차선, 움직임 및 충돌 시점을 분석하고 있습니다."}
        </p>
      </div>

      <div className="progress-card">
        <div className="progress-title">
          <strong>
            <Icon name="progress_activity" className="spinning" />
            실시간 분석 진행률
          </strong>
          <strong className="progress-number">{progress}%</strong>
        </div>

        <div className="progress-track">
          <div className="progress-bar" style={{ width: `${progress}%` }} />
        </div>

        {MILESTONES.map((milestone, index) => (
          <Milestone
            key={milestone.text}
            number={String(index + 1)}
            text={milestone.text}
            done={progress >= milestone.doneAt}
          />
        ))}
      </div>

      <div className="eta-row">
        <span>
          분석 예상 소요 시간:
          <strong> 약 18초</strong>
        </span>
        <button type="button" onClick={onFastForward}>
          빠른 진행(테스트용)
        </button>
      </div>
    </div>
  );
}

export default AnalyzingStage;
