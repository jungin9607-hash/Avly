import { useState } from "react";
import Icon from "../../../components/ui/Icon";
import { STAGE } from "../constants";

function ConsentStage({ onStart, setStage }) {
  const [agreeAnalysis, setAgreeAnalysis] = useState(true);
  const [agreeQuiz, setAgreeQuiz] = useState(true);

  const allAgree = agreeAnalysis && agreeQuiz;

  const handleAgreeAll = (checked) => {
    setAgreeAnalysis(checked);
    setAgreeQuiz(checked);
  };

  return (
    <div className="modal-stage">
      <div>
        <h3>블랙박스 영상 수집 동의</h3>
        <p className="modal-description">아래 항목을 확인해 주세요.</p>
      </div>

      <div className="consent-box">
        <label className="consent-all">
          <input
            type="checkbox"
            checked={allAgree}
            onChange={(event) => handleAgreeAll(event.target.checked)}
          />
          <strong>전체 항목 동의</strong>
        </label>

        <div className="divider" />

        <label className="consent-item">
          <input
            type="checkbox"
            checked={agreeAnalysis}
            onChange={(event) => setAgreeAnalysis(event.target.checked)}
          />
          <div>
            <strong>교통사고 분석을 위한 영상 수집 및 AI 분석 처리 동의</strong>
            <p>블랙박스 프레임, 차선, 차량 객체 및 움직임 분석을 위해 영상을 처리합니다.</p>
          </div>
        </label>

        <div className="divider" />

        <label className="consent-item">
          <input
            type="checkbox"
            checked={agreeQuiz}
            onChange={(event) => setAgreeQuiz(event.target.checked)}
          />
          <div>
            <strong>사고 예방 퀴즈 활용 동의</strong>
            <p>
              개인정보를 비식별 처리한 후 향후 사고 예방 콘텐츠 개선에 활용할 수 있습니다.
            </p>
          </div>
        </label>
      </div>

      <button type="button" className="modal-primary-button" onClick={onStart}>
        {allAgree ? "동의하고 영상 분석 시작하기" : "영상 분석 시작하기"}
        <Icon name="arrow_forward" />
      </button>

      <div className="simulation-buttons">
        <span>예외 상황 시뮬레이션</span>
        <button type="button" onClick={() => setStage(STAGE.ERROR_FORMAT)}>
          지원하지 않는 파일
        </button>
        <button type="button" onClick={() => setStage(STAGE.UNSUPPORTED)}>
          분석 불가 사고
        </button>
      </div>
    </div>
  );
}

export default ConsentStage;
