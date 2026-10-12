import Icon from "../../../components/ui/Icon";

function ResultStage({ onMismatch, onConfirm }) {
  return (
    <div className="modal-stage">
      <div>
        <h3 className="result-main-title">AI가 판독한 사고 상황 제시</h3>
        <p className="modal-description">실제 사고 상황과 일치하는지 확인해 주세요.</p>
      </div>

      <div className="result-card">
        <div className="result-header">
          <div>
            <span className="result-type">판정 사고 유형</span>
          </div>
          <h4>차선 변경 중 접촉 사고</h4>
        </div>

        <div>
          <span className="small-label">상황 요약</span>
          <p className="situation-summary">
            직진 차로를 정상 주행 중인 내 차량 측면으로 상대 차량이 방향지시등 미점등 상태에서
            진입하여 발생한 접촉 사고
          </p>
        </div>

        <div className="fault-result">
          <div className="fault-numbers">
            <div>
              <span>내 과실</span>
              <strong className="my-fault">20%</strong>
            </div>

            <div className="fault-center">
              <strong>VS</strong>
              <span>충돌 직전 차선 침범 감지</span>
            </div>

            <div>
              <span>상대방 과실</span>
              <strong className="other-fault">80%</strong>
            </div>
          </div>

          <div className="fault-bar">
            <div className="fault-bar-me" />
            <div className="fault-bar-other" />
          </div>

          <div className="fault-tags">
            <span>기본 30:70</span>
            <span className="blue-tag">깜빡이 미점등</span>
            <span>직진 우선권 인정</span>
          </div>
        </div>
      </div>

      <div className="result-buttons">
        <button type="button" className="secondary-action" onClick={onMismatch}>
          <Icon name="replay" />
          사고 상황이 일치하지 않습니다
        </button>

        <button type="button" className="modal-primary-button" onClick={onConfirm}>
          사고 상황이 일치합니다
          <Icon name="arrow_forward" />
        </button>
      </div>
    </div>
  );
}

export default ResultStage;
