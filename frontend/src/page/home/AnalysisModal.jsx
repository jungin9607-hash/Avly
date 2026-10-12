import Icon from "../../components/ui/Icon";
import { StepIndicator } from "./ModalParts";
import ConsentStage from "./stages/ConsentStage";
import ErrorFormatStage from "./stages/ErrorFormatStage";
import QuestionnaireStage from "./stages/QuestionnaireStage";
import AnalyzingStage from "./stages/AnalyzingStage";
import UnsupportedStage from "./stages/UnsupportedStage";
import ResultStage from "./stages/ResultStage";
import ReanalysisStage from "./stages/ReanalysisStage";
import { MODAL_INFO, STAGE } from "./constants";

function AnalysisModal({
  stage,
  setStage,
  selectedFile,
  progress,
  onClose,
  onRetryUpload,
  onStartAnalysis,
  onFastForward,
  onConfirmResult,
}) {
  const info = MODAL_INFO[stage] ?? MODAL_INFO[STAGE.CONSENT];

  return (
    <div
      className="modal-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="analysis-modal">
        <div className="modal-header">
          <div className="modal-header-info">
            <div>
              <strong>{info.title}</strong>
              <p>{info.subtitle}</p>
            </div>
          </div>

          <div className="modal-header-right">
            {info.step && <StepIndicator current={info.step} />}

            <button className="modal-close" type="button" onClick={onClose}>
              <Icon name="close" />
            </button>
          </div>
        </div>

        <div className="modal-body">
          {stage === STAGE.CONSENT && (
            <ConsentStage
              setStage={setStage}
              onStart={() => onStartAnalysis(STAGE.QUESTIONNAIRE)}
            />
          )}

          {stage === STAGE.ERROR_FORMAT && (
            <ErrorFormatStage fileName={selectedFile?.name} onRetry={onRetryUpload} />
          )}

          {stage === STAGE.QUESTIONNAIRE && (
            <QuestionnaireStage onSubmit={() => onStartAnalysis(STAGE.RESULT, true)} />
          )}

          {(stage === STAGE.ANALYZING || stage === STAGE.REANALYZING) && (
            <AnalyzingStage stage={stage} progress={progress} onFastForward={onFastForward} />
          )}

          {stage === STAGE.UNSUPPORTED && <UnsupportedStage onRetry={onRetryUpload} />}

          {stage === STAGE.RESULT && (
            <ResultStage
              onMismatch={() => setStage(STAGE.REANALYSIS)}
              onConfirm={onConfirmResult}
            />
          )}

          {stage === STAGE.REANALYSIS && (
            <ReanalysisStage
              onBack={() => setStage(STAGE.RESULT)}
              onSubmit={() => onStartAnalysis(STAGE.RESULT, true)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default AnalysisModal;
