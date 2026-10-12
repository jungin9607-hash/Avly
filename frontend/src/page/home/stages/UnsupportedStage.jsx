import Icon from "../../../components/ui/Icon";

const UNSUPPORTED_TARGETS = [
  "보행자 단독 사고",
  "다중 연쇄 추돌 사고",
  "이륜차 단독 사고",
  "차선 식별이 불가능한 영상",
];

function UnsupportedStage({ onRetry }) {
  return (
    <div className="modal-stage center-stage">
      <div className="error-icon">
        <Icon name="car_crash" />
      </div>

      <h3>지원하지 않는 사고 유형</h3>

      <p className="modal-description">
        현재 영상은 AI가 자동 분석하기 어려운 사고 유형이거나 영상에서 차선 및 차량 객체 식별이
        어렵습니다.
      </p>

      <div className="unsupported-box">
        <strong>현재 미지원 대상</strong>
        <ul>
          {UNSUPPORTED_TARGETS.map((target) => (
            <li key={target}>{target}</li>
          ))}
        </ul>
      </div>

      <button type="button" className="modal-primary-button" onClick={onRetry}>
        다른 사고 영상 업로드하기
      </button>
    </div>
  );
}

export default UnsupportedStage;
