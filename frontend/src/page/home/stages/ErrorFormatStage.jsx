import Icon from "../../../components/ui/Icon";

function ErrorFormatStage({ fileName, onRetry }) {
  return (
    <div className="modal-stage center-stage">
      <div className="error-icon">
        <Icon name="warning" />
      </div>

      <h3>지원하지 않는 형식 또는 용량 초과</h3>

      <p className="modal-description">
        업로드 가능한 파일 형식은 MP4, MOV, AVI이며 단일 파일의 최대 용량은 500MB입니다.
      </p>

      <div className="spec-box">
        <div>
          <span>선택된 파일</span>
          <strong>{fileName ?? "unsupported_file.zip"}</strong>
        </div>
        <div>
          <span>허용 포맷</span>
          <strong>MP4 / MOV / AVI</strong>
        </div>
        <div>
          <span>최대 용량</span>
          <strong>500MB</strong>
        </div>
      </div>

      <button type="button" className="modal-primary-button" onClick={onRetry}>
        <Icon name="upload_file" />
        다시 업로드하기
      </button>
    </div>
  );
}

export default ErrorFormatStage;
