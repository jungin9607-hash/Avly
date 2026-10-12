import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../../components/layout/Header";
import Footer from "../../components/layout/Footer";
import Icon from "../../components/ui/Icon";
import AnalysisModal from "./AnalysisModal";
import { useAnalysisProgress } from "./useAnalysisProgress";
import { isValidVideoFile } from "./validateFile";
import { GUIDES, STAGE } from "./constants";
import "./home.css";

function Home() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [stage, setStage] = useState(STAGE.CONSENT);

  const { progress, start, fastForward, stop } = useAnalysisProgress(stage, setStage);

  const openModal = (nextStage = STAGE.CONSENT) => {
    setStage(nextStage);
    setModalOpen(true);
  };

  const closeModal = () => {
    stop();
    setModalOpen(false);
  };

  const handleFile = (file) => {
    if (!file) return;

    setSelectedFile(file);
    openModal(isValidVideoFile(file) ? STAGE.CONSENT : STAGE.ERROR_FORMAT);
  };

  const handleBrowseClick = () => fileInputRef.current?.click();

  const handleRetryUpload = () => {
    closeModal();
    handleBrowseClick();
  };

  const handleConfirmResult = () => {
    setModalOpen(false);
    navigate("/report");
  };

  const fileSize = selectedFile ? (selectedFile.size / 1024 / 1024).toFixed(1) : "38.5";
  const fileName = selectedFile?.name ?? "블랙박스_시연용_차선사고.mp4";

  return (
    <div className="home-page">
      <Header />

      <main className="home-main">
        <div className="home-container">
          {/* Breadcrumb */}

          <div className="breadcrumb">
            <span>홈</span>

            <Icon name="chevron_right" />

            <strong>
              블랙박스 영상 업로드
            </strong>
          </div>

          <div className="home-grid">
            {/* ==========================================
                LEFT
            ========================================== */}

            <div className="home-left">
              {/* Upload */}

              <section
                className="upload-box"
                onDrop={(event) => {
                  event.preventDefault();
                  handleFile(event.dataTransfer.files?.[0]);
                }}
                onDragOver={(event) => event.preventDefault()}
              >
                <div className="upload-decoration" />

                <div className="upload-content">
                  <div className="upload-icon">
                    <Icon name="cloud_upload" />
                  </div>


                  <p>
                    MP4, MOV, AVI 포맷 지원 ·
                    단일 파일 최대{" "}
                    <strong>500MB</strong> 이내 권장
                  </p>

                  <button
                    className="primary-button"
                    type="button"
                    onClick={handleBrowseClick}
                  >
                    <Icon name="add_circle" />

                    블랙박스 영상 업로드
                  </button>

                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".mp4,.mov,.avi,video/mp4,video/quicktime,video/x-msvideo"
                    onChange={(event) => handleFile(event.target.files?.[0])}
                    hidden
                  />
                </div>
              </section>

              {/* File Card */}

              <section className="file-card">
                <div className="file-card-title">
                  <div>
                    <Icon name="movie" />

                    <span>
                      등록된 시연 파일 목록
                    </span>
                  </div>

                  <span>1개 준비됨</span>
                </div>

                <div className="file-item">
                  <div className="file-information">
                    <div className="file-icon">
                      <Icon name="video_file" />
                    </div>

                    <div className="file-content">
                      <div className="file-name-row">
                        <strong>
                          {fileName}
                        </strong>

                        <span className="file-tag">
                          FHD 60fps
                        </span>
                      </div>

                      <div className="file-meta">
                        <span>
                          {fileSize} MB
                        </span>

                        <span>·</span>

                        <span>
                          재생시간 00:24
                        </span>

                        <span>·</span>

                        <span className="ready-status">
                          <Icon name="check_circle" />

                          준비 완료
                        </span>
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="demo-button"
                    onClick={() => openModal()}
                  >
                    <Icon name="bolt" />

                    단계별 AI 정밀 분석 팝업 시연
                  </button>
                </div>
              </section>
            </div>

            {/* ==========================================
                RIGHT
            ========================================== */}

            <aside className="home-right">
              <section className="guide-card">
                <div className="guide-title">
                  <div className="guide-title-icon">
                    <Icon name="lightbulb" />
                  </div>

                  <h3>
                    정확한 분석을 위한 영상 가이드
                  </h3>
                </div>

                <div className="guide-list">
                  {GUIDES.map((guide, index) => (
                    <GuideItem key={guide.title} number={String(index + 1)} title={guide.title}>
                      {guide.text}
                    </GuideItem>
                  ))}
                </div>

                <div className="analysis-time">
                  <div>
                    <Icon name="speed" />

                    <strong>
                      실시간 평균 분석 소요 시간
                    </strong>
                  </div>

                  <strong className="analysis-time-value">
                    약 18초
                  </strong>
                </div>
              </section>

              <div className="legal-mini">
                <Icon name="policy" />

                <p>
                  에블리는 손해보험협회 과실비율
                  인정기준과 판례 데이터를 참고하여
                  예상 결과를 제공합니다. 최종 법적
                  효력은 보험사 합의 또는 법원
                  판결에 따릅니다.
                </p>
              </div>
            </aside>
          </div>
        </div>
      </main>

      {/* ==================================================
          FOOTER
      ================================================== */}

      <Footer />

      {modalOpen && (
        <AnalysisModal
          stage={stage}
          setStage={setStage}
          selectedFile={selectedFile}
          progress={progress}
          onClose={closeModal}
          onRetryUpload={handleRetryUpload}
          onStartAnalysis={start}
          onFastForward={fastForward}
          onConfirmResult={handleConfirmResult}
        />
      )}
    </div>
  );
}

function GuideItem({ number, title, children }) {
  return (
    <div className="guide-item">
      <div className="guide-number">{number}</div>
      <div>
        <strong>{title}</strong>
        <p>{children}</p>
      </div>
    </div>
  );
}

export default Home;
