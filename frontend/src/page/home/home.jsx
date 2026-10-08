import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import avlyBrand from "../../assets/avly-brand.png";
import avlyMascot from "../../assets/avly-mascot.png";
import "./home.css";

function Home() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const analysisTimerRef = useRef(null);
  const analysisNextStageRef = useRef("questionnaire");

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileAnalysisOpen, setMobileAnalysisOpen] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [stage, setStage] = useState("consent");

  const [agreeAnalysis, setAgreeAnalysis] = useState(true);
  const [agreeQuiz, setAgreeQuiz] = useState(true);

  const [progress, setProgress] = useState(0);

  const [answers, setAnswers] = useState({
    blinker: "no",
    speed: "limit_ok",
    weather: "clear",
  });

  const [reanalyzeReason, setReanalyzeReason] =
    useState("not_lane_change");

  /* ===============================
     파일 관련
  =============================== */

  const validateFile = (file) => {
    const allowedExtensions = ["mp4", "mov", "avi"];

    const extension = file.name
      .split(".")
      .pop()
      .toLowerCase();

    const maxSize = 500 * 1024 * 1024;

    if (
      !allowedExtensions.includes(extension) ||
      file.size > maxSize
    ) {
      setSelectedFile(file);
      setStage("errorFormat");
      setModalOpen(true);
      return false;
    }

    return true;
  };

  const handleFile = (file) => {
    if (!file) return;

    if (!validateFile(file)) {
      return;
    }

    setSelectedFile(file);

    setStage("consent");
    setModalOpen(true);
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];

    handleFile(file);
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const handleDrop = (event) => {
    event.preventDefault();

    const file = event.dataTransfer.files?.[0];

    handleFile(file);
  };

  const handleDragOver = (event) => {
    event.preventDefault();
  };

  /* ===============================
     팝업
  =============================== */

  const openDemoModal = () => {
    setStage("consent");
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);

    if (analysisTimerRef.current) {
      clearInterval(analysisTimerRef.current);
    }
  };

  /* ===============================
     동의
  =============================== */

  const allAgree = agreeAnalysis && agreeQuiz;

  const handleAgreeAll = (checked) => {
    setAgreeAnalysis(checked);
    setAgreeQuiz(checked);
  };

  /* ===============================
     AI 분석 진행
  =============================== */

  useEffect(() => {
    if (stage !== "analyzing" && stage !== "reanalyzing") {
      return;
    }

    if (analysisTimerRef.current) {
      clearInterval(analysisTimerRef.current);
    }

    const steps = [50, 85, 100];
    let index = 0;

    analysisTimerRef.current = setInterval(() => {
      const next = steps[index];

      setProgress(next);

      index += 1;

      if (index >= steps.length) {
        clearInterval(analysisTimerRef.current);

        setTimeout(() => {
          setStage(analysisNextStageRef.current);
        }, 900);
      }
    }, 1000);

    return () => {
      if (analysisTimerRef.current) {
        clearInterval(analysisTimerRef.current);
      }
    };
  }, [stage]);

  const startAnalysis = (nextStage = "questionnaire", reanalysis = false) => {
    setProgress(15);
    analysisNextStageRef.current = nextStage;
    setStage(reanalysis ? "reanalyzing" : "analyzing");
  };

  const fastForward = () => {
    if (analysisTimerRef.current) {
      clearInterval(analysisTimerRef.current);
    }

    setProgress(100);

    setTimeout(() => {
      setStage(analysisNextStageRef.current);
    }, 300);
  };

  /* ===============================
     모달 제목
  =============================== */

  const modalInfo = {
    consent: {
      icon: "policy",
      title: "블랙박스 영상 AI 분석 동의",
      step: 1,
    },

    errorFormat: {
      icon: "warning",
      title: "지원하지 않는 형식 또는 용량 초과",
      subtitle: "업로드 파일 사양 확인",
      step: null,
    },

      analyzing: {
      icon: "memory",
      title: "에블리 AI가 영상을 정밀 분석하고 있습니다",
      subtitle: "컴퓨터 비전 텔레메트리 추출 중",
      step: 2,
    },

      reanalyzing: {
        icon: "memory",
        title: "질문 내용을 반영해 재분석 중입니다",
        subtitle: "답변을 반영하여 사고 상황을 다시 분석하고 있습니다",
        step: 2,
      },

    questionnaire: {
      icon: "help_center",
      title: "정확한 과실 분석을 위한 AI 추가 질문",
      step: 3,
    },


    unsupported: {
      icon: "car_crash",
      title: "지원하지 않는 사고 유형",
      subtitle: "AI 판독 예외 케이스 감지",
      step: null,
    },

    resultSummary: {
      icon: "fact_check",
      title: "AI가 판독한 사고 상황 제시",
      step: 4,
    },

    reanalysis: {
      icon: "autorenew",
      title: "사고 정황 재분석 요청",
      subtitle: "가중치 재조정 파라미터 선택",
      step: null,
    },
  };

  const currentModal =
    modalInfo[stage] ?? modalInfo.consent;

  const fileSize = selectedFile
    ? (selectedFile.size / 1024 / 1024).toFixed(1)
    : "38.5";

  const fileName =
    selectedFile?.name ??
    "블랙박스_시연용_차선사고.mp4";

  return (
    <div className="home-page">
      {/* ==================================================
          HEADER
      ================================================== */}

      <header className="home-header">
        <div className="header-inner">
          <div className="header-left">
            <Link className="brand" to="/">
              <img
                className="brand-logo brand-header-logo"
                src={avlyBrand}
                alt="에블리 캐릭터와 로고"
              />

              <div className="brand-text">
                <strong>Avly</strong>
                <span className="brand-korean">
                  에블리
                </span>

                <span className="brand-divider">
                  |
                </span>

                <span className="brand-description">
                  AI 교통사고 과실 분석
                </span>
              </div>
            </Link>

            <nav className="navigation" aria-label="메인 메뉴">
              <Link
                className="nav-item nav-active"
                to="/home"
              >
                홈
              </Link>

              <Link
                className="nav-item"
                to="/report"
              >
                분석 결과
              </Link>

              <div className="nav-item-group">
                <button
                  type="button"
                  className="nav-item nav-trigger"
                  aria-haspopup="true"
                >
                  사고 분석
                </button>

                <div className="mega-menu" aria-label="사고 분석 메뉴">
                  <Link to="/time" className="mega-menu-item">
                    사고 순간 타임라인
                  </Link>
                  <Link to="/law" className="mega-menu-item">
                    유사 판례 분석
                  </Link>
                </div>
              </div>

              <Link
                className="nav-item"
                to="/home"
              >
                사고 예방
              </Link>
            </nav>
          </div>

          <div className="header-right">
            <button
              type="button"
              className="mobile-menu-toggle"
              aria-label="메뉴 열기"
              aria-expanded={mobileMenuOpen}
              onClick={() => setMobileMenuOpen((prev) => !prev)}
            >
              <span />
              <span />
              <span />
            </button>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="mobile-menu-overlay" onClick={() => setMobileMenuOpen(false)}>
            <aside className="mobile-menu-panel" role="menu" aria-label="모바일 메뉴" onClick={(event) => event.stopPropagation()}>
              <div className="mobile-menu-header">
                <Link to="/" className="mobile-menu-brand">
                  <img className="brand-logo" src={avlyMascot} alt="" />
                  <span><strong>Avly</strong> <small>교통사고 AI 분석</small></span>
                </Link>
                <button type="button" className="mobile-menu-close" aria-label="메뉴 닫기" onClick={() => setMobileMenuOpen(false)}>
                  <span className="material-symbols-outlined">close</span>
                </button>
              </div>
              <nav className="mobile-menu-list">
                <Link to="/home" className="mobile-menu-item active" onClick={() => setMobileMenuOpen(false)}>
                  <span className="material-symbols-outlined">home</span><span>홈</span>
                  <small className="mobile-menu-current">현재 화면</small>
                </Link>
                <Link to="/report" className="mobile-menu-item" onClick={() => setMobileMenuOpen(false)}>
                  <span className="material-symbols-outlined">analytics</span><span>분석 결과</span>
                </Link>
                <div className="mobile-menu-analysis-row">
                  <button type="button" className="mobile-menu-item mobile-menu-analysis" aria-expanded={mobileAnalysisOpen} aria-controls="home-analysis-submenu" onClick={() => setMobileAnalysisOpen((open) => !open)}>
                    <span className="material-symbols-outlined">error_outline</span><span>사고 분석</span><span className="material-symbols-outlined">expand_more</span>
                  </button>
                </div>
                {mobileAnalysisOpen && (
                  <div className="mobile-submenu" id="home-analysis-submenu">
                    <Link to="/time" onClick={() => setMobileMenuOpen(false)}><span>사고 순간 타임라인</span><small>보기 &gt;</small></Link>
                    <Link to="/law" onClick={() => setMobileMenuOpen(false)}><span>유사 판례 분석</span><small>보기 &gt;</small></Link>
                  </div>
                )}
                <Link to="/home" className="mobile-menu-item" onClick={() => setMobileMenuOpen(false)}>
                  <span className="material-symbols-outlined">verified_user</span><span>사고 예방</span>
                </Link>
              </nav>
            </aside>
          </div>
        )}
      </header>

      {/* ==================================================
          MAIN
      ================================================== */}

      <main className="home-main">
        <div className="home-container">
          {/* Breadcrumb */}

          <div className="breadcrumb">
            <span>홈</span>

            <span className="material-symbols-outlined">
              chevron_right
            </span>

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
                onDrop={handleDrop}
                onDragOver={handleDragOver}
              >
                <div className="upload-decoration" />

                <div className="upload-content">
                  <div className="upload-icon">
                    <span className="material-symbols-outlined">
                      cloud_upload
                    </span>
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
                    <span className="material-symbols-outlined">
                      add_circle
                    </span>

                    블랙박스 영상 업로드
                  </button>

                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".mp4,.mov,.avi,video/mp4,video/quicktime,video/x-msvideo"
                    onChange={handleFileChange}
                    hidden
                  />
                </div>
              </section>

              {/* File Card */}

              <section className="file-card">
                <div className="file-card-title">
                  <div>
                    <span className="material-symbols-outlined">
                      movie
                    </span>

                    <span>
                      등록된 시연 파일 목록
                    </span>
                  </div>

                  <span>1개 준비됨</span>
                </div>

                <div className="file-item">
                  <div className="file-information">
                    <div className="file-icon">
                      <span className="material-symbols-outlined">
                        video_file
                      </span>
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
                          <span className="material-symbols-outlined">
                            check_circle
                          </span>

                          준비 완료
                        </span>
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="demo-button"
                    onClick={openDemoModal}
                  >
                    <span className="material-symbols-outlined">
                      bolt
                    </span>

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
                    <span className="material-symbols-outlined">
                      lightbulb
                    </span>
                  </div>

                  <h3>
                    정확한 분석을 위한 영상 가이드
                  </h3>
                </div>

                <div className="guide-list">
                  <GuideItem
                    number="1"
                    title="전방 블랙박스 영상 권장"
                  >
                    상대 차량의 진입 각도, 도로
                    차선(실선·점선), 노면 표시 및
                    신호등 점등 상태가 뚜렷하게
                    식별될수록 분석 오차가 감소합니다.
                  </GuideItem>

                  <GuideItem
                    number="2"
                    title="사고 전후 15초 내외 구간"
                  >
                    충돌 시점 기준 최소 10초 전
                    진입 단계부터 충돌 직후 5초까지
                    포함하는 것을 권장합니다.
                  </GuideItem>

                  <GuideItem
                    number="3"
                    title="음성 녹음 여부 무관"
                  >
                    에블리 AI는 시각 좌표 및 차량
                    움직임을 분석하며 내부 대화나
                    오디오는 분석에 사용하지 않습니다.
                  </GuideItem>
                </div>

                <div className="analysis-time">
                  <div>
                    <span className="material-symbols-outlined">
                      speed
                    </span>

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
                <span className="material-symbols-outlined">
                  policy
                </span>

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

      <footer className="home-footer">
        <div className="footer-inner">
          <div className="footer-notice">
            <span className="material-symbols-outlined">
              verified_user
            </span>

            <div>
              <strong>
                법적 책임 고지 및 안내
              </strong>

              <p>
                본 서비스는 AI 영상 분석 및
                과실비율 인정기준·판례 데이터를
                기반으로 제공되는 참고자료이며,
                확정 판결을 대신하지 않습니다.
              </p>
            </div>
          </div>

          <div className="footer-bottom">
            <div>
              <strong>Avly</strong>
              <span> (에블리)</span>
              <span> · </span>
              <a href="#">이용약관</a>
              <span> · </span>
              <a href="#">
                개인정보처리방침
              </a>
              <span> · </span>
              <a href="#">
                고객지원센터
              </a>
            </div>

            <span>
              © 2026 Avly
            </span>
          </div>
        </div>
      </footer>

      {/* ==================================================
          ANALYSIS MODAL
      ================================================== */}

      {modalOpen && (
        <div
          className="modal-overlay"
          onMouseDown={(event) => {
            if (
              event.target === event.currentTarget
            ) {
              closeModal();
            }
          }}
        >
          <div className="analysis-modal">
            {/* Modal Header */}

            <div className="modal-header">
              <div className="modal-header-info">
                <div>
                  <strong>
                    {currentModal.title}
                  </strong>

                  <p>
                    {currentModal.subtitle}
                  </p>
                </div>
              </div>

              <div className="modal-header-right">
                {currentModal.step && (
                  <StepIndicator
                    current={
                      currentModal.step
                    }
                  />
                )}

                <button
                  className="modal-close"
                  type="button"
                  onClick={closeModal}
                >
                  <span className="material-symbols-outlined">
                    close
                  </span>
                </button>
              </div>
            </div>

            {/* Modal Body */}

            <div className="modal-body">
              {/* ======================================
                  1. 동의
              ====================================== */}

              {stage === "consent" && (
                <div className="modal-stage">
                  <div>
                    <h3>
                      블랙박스 영상 수집 동의
                    </h3>

                    <p className="modal-description">
                      아래 항목을 확인해 주세요.
                    </p>
                  </div>

                  <div className="consent-box">
                    <label className="consent-all">
                      <input
                        type="checkbox"
                        checked={allAgree}
                        onChange={(event) =>
                          handleAgreeAll(
                            event.target
                              .checked
                          )
                        }
                      />

                      <strong>
                        전체 항목 동의
                      </strong>
                    </label>

                    <div className="divider" />

                    <label className="consent-item">
                      <input
                        type="checkbox"
                        checked={
                          agreeAnalysis
                        }
                        onChange={(event) =>
                          setAgreeAnalysis(
                            event.target
                              .checked
                          )
                        }
                      />

                      <div>
                        <strong>
                          교통사고 분석을 위한
                          영상 수집 및 AI 분석
                          처리 동의
                        </strong>

                        <p>
                          블랙박스 프레임,
                          차선, 차량 객체 및
                          움직임 분석을 위해
                          영상을 처리합니다.
                        </p>
                      </div>
                    </label>

                    <div className="divider" />

                    <label className="consent-item">
                      <input
                        type="checkbox"
                        checked={agreeQuiz}
                        onChange={(event) =>
                          setAgreeQuiz(
                            event.target
                              .checked
                          )
                        }
                      />

                      <div>
                        <strong>
                          사고 예방 퀴즈 활용
                          동의
                        </strong>

                        <p>
                          개인정보를 비식별
                          처리한 후 향후 사고
                          예방 콘텐츠 개선에
                          활용할 수 있습니다.
                        </p>
                      </div>
                    </label>
                  </div>

                  <button
                    type="button"
                    className="modal-primary-button"
                    onClick={() => startAnalysis("questionnaire")}
                  >
                    {allAgree
                      ? "동의하고 영상 분석 시작하기"
                      : "영상 분석 시작하기"}

                    <span className="material-symbols-outlined">
                      arrow_forward
                    </span>
                  </button>

                  <div className="simulation-buttons">
                    <span>
                      예외 상황 시뮬레이션
                    </span>

                    <button
                      type="button"
                      onClick={() =>
                        setStage(
                          "errorFormat"
                        )
                      }
                    >
                      지원하지 않는 파일
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        setStage(
                          "unsupported"
                        )
                      }
                    >
                      분석 불가 사고
                    </button>
                  </div>
                </div>
              )}

              {/* ======================================
                  파일 오류
              ====================================== */}

              {stage === "errorFormat" && (
                <div className="modal-stage center-stage">
                  <div className="error-icon">
                    <span className="material-symbols-outlined">
                      warning
                    </span>
                  </div>

                  <h3>
                    지원하지 않는 형식 또는
                    용량 초과
                  </h3>

                  <p className="modal-description">
                    업로드 가능한 파일 형식은
                    MP4, MOV, AVI이며 단일
                    파일의 최대 용량은
                    500MB입니다.
                  </p>

                  <div className="spec-box">
                    <div>
                      <span>
                        선택된 파일
                      </span>

                      <strong>
                        {selectedFile?.name ??
                          "unsupported_file.zip"}
                      </strong>
                    </div>

                    <div>
                      <span>
                        허용 포맷
                      </span>

                      <strong>
                        MP4 / MOV / AVI
                      </strong>
                    </div>

                    <div>
                      <span>
                        최대 용량
                      </span>

                      <strong>
                        500MB
                      </strong>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="modal-primary-button"
                    onClick={() => {
                      closeModal();
                      handleBrowseClick();
                    }}
                  >
                    <span className="material-symbols-outlined">
                      upload_file
                    </span>

                    다시 업로드하기
                  </button>
                </div>
              )}

              {/* ======================================
                  2. 질문
              ====================================== */}

              {stage ===
                "questionnaire" && (
                <div className="modal-stage">
                  <div>

                    <h3>
                      정확한 분석을 위한
                      추가 질문
                    </h3>

                  </div>

                  <QuestionCard
                    number="1"
                    question="충돌 직전 상대 차량이 방향지시등을 점등했나요?"
                  >
                    <RadioOption
                      name="blinker"
                      value="no"
                      checked={
                        answers.blinker ===
                        "no"
                      }
                      onChange={() =>
                        setAnswers({
                          ...answers,
                          blinker: "no",
                        })
                      }
                      label="켜지 않았다"
                    />

                    <RadioOption
                      name="blinker"
                      value="yes"
                      checked={
                        answers.blinker ===
                        "yes"
                      }
                      onChange={() =>
                        setAnswers({
                          ...answers,
                          blinker: "yes",
                        })
                      }
                      label="켜져 있었다"
                    />

                    <RadioOption
                      name="blinker"
                      value="unknown"
                      checked={
                        answers.blinker ===
                        "unknown"
                      }
                      onChange={() =>
                        setAnswers({
                          ...answers,
                          blinker:
                            "unknown",
                        })
                      }
                      label="인지하지 못함"
                    />
                  </QuestionCard>

                  <QuestionCard
                    number="2"
                    question="내 차량은 제한속도를 준수 중이었나요?"
                  >
                    <RadioOption
                      name="speed"
                      checked={
                        answers.speed ===
                        "limit_ok"
                      }
                      onChange={() =>
                        setAnswers({
                          ...answers,
                          speed:
                            "limit_ok",
                        })
                      }
                      label="규정속도 준수"
                    />

                    <RadioOption
                      name="speed"
                      checked={
                        answers.speed ===
                        "limit_over"
                      }
                      onChange={() =>
                        setAnswers({
                          ...answers,
                          speed:
                            "limit_over",
                        })
                      }
                      label="규정속도 초과"
                    />
                  </QuestionCard>

                  <QuestionCard
                    number="3"
                    question="사고 당시 시야 장애 요인이 있었나요?"
                  >
                    <RadioOption
                      name="weather"
                      checked={
                        answers.weather ===
                        "clear"
                      }
                      onChange={() =>
                        setAnswers({
                          ...answers,
                          weather: "clear",
                        })
                      }
                      label="맑음 / 시야 확보"
                    />

                    <RadioOption
                      name="weather"
                      checked={
                        answers.weather ===
                        "bad"
                      }
                      onChange={() =>
                        setAnswers({
                          ...answers,
                          weather: "bad",
                        })
                      }
                      label="야간 / 우천 / 안개"
                    />
                  </QuestionCard>

                  <button
                    type="button"
                    className="modal-primary-button"
                    onClick={() => startAnalysis("resultSummary", true)}
                  >
                    답변 제출하고 재분석 하기
                  </button>
                </div>
              )}

              {/* ======================================
                  3. 분석 중
              ====================================== */}

              {(stage === "analyzing" || stage === "reanalyzing") && (
                <div className="modal-stage">
                  <div className="analysis-heading">
                    <span className="analyzing-badge">
                      {stage === "reanalyzing"
                        ? "답변 반영 AI 재분석 중"
                        : "AI 비전 심층 추론 엔진 가동 중"}
                    </span>

                    <h3>
                      {stage === "reanalyzing"
                        ? "답변 내용을 반영해 사고 상황을 재분석하고 있습니다"
                        : "에블리 AI가 영상을 정밀 분석하고 있습니다"}
                    </h3>

                    <p className="modal-description">
                      {stage === "reanalyzing"
                        ? "선택하신 답변을 영상 분석 및 과실 판단에 반영하고 있습니다."
                        : "차량 객체와 차선, 움직임 및 충돌 시점을 분석하고 있습니다."}
                    </p>
                  </div>

                  <div className="progress-card">
                    <div className="progress-title">
                      <strong>
                        <span className="material-symbols-outlined spinning">
                          progress_activity
                        </span>

                        실시간 분석 진행률
                      </strong>

                      <strong className="progress-number">
                        {progress}%
                      </strong>
                    </div>

                    <div className="progress-track">
                      <div
                        className="progress-bar"
                        style={{
                          width: `${progress}%`,
                        }}
                      />
                    </div>

                    <Milestone
                      number="1"
                      text="영상 디코딩 및 텔레메트리 추출"
                      done={progress >= 15}
                    />

                    <Milestone
                      number="2"
                      text="충돌 전후 프레임 객체 인식"
                      done={progress >= 85}
                    />

                    <Milestone
                      number="3"
                      text="과실비율 기준 및 판례 매칭"
                      done={progress >= 100}
                    />
                  </div>

                  <div className="eta-row">
                    <span>
                      분석 예상 소요 시간:
                      <strong>
                        {" "}
                        약 18초
                      </strong>
                    </span>

                    <button
                      type="button"
                      onClick={
                        fastForward
                      }
                    >
                      빠른 진행(테스트용)
                    </button>
                  </div>
                </div>
              )}

              {/* ======================================
                  분석 불가
              ====================================== */}

              {stage === "unsupported" && (
                <div className="modal-stage center-stage">
                  <div className="error-icon">
                    <span className="material-symbols-outlined">
                      car_crash
                    </span>
                  </div>

                  <h3>
                    지원하지 않는 사고 유형
                  </h3>

                  <p className="modal-description">
                    현재 영상은 AI가
                    자동 분석하기 어려운
                    사고 유형이거나 영상에서
                    차선 및 차량 객체 식별이
                    어렵습니다.
                  </p>

                  <div className="unsupported-box">
                    <strong>
                      현재 미지원 대상
                    </strong>

                    <ul>
                      <li>
                        보행자 단독 사고
                      </li>

                      <li>
                        다중 연쇄 추돌 사고
                      </li>

                      <li>
                        이륜차 단독 사고
                      </li>

                      <li>
                        차선 식별이 불가능한
                        영상
                      </li>
                    </ul>
                  </div>

                  <button
                    type="button"
                    className="modal-primary-button"
                    onClick={() => {
                      closeModal();
                      handleBrowseClick();
                    }}
                  >
                    다른 사고 영상
                    업로드하기
                  </button>
                </div>
              )}

              {/* ======================================
                  4. 결과
              ====================================== */}

              {stage ===
                "resultSummary" && (
                <div className="modal-stage">
                  <div>
                    

                    <h3 className="result-main-title">
                      AI가 판독한 사고 상황
                      제시
                    </h3>

                    <p className="modal-description">
                      실제 사고 상황과
                      일치하는지 확인해 주세요.
                    </p>
                  </div>

                  <div className="result-card">
                    <div className="result-header">
                      <div>
                        <span className="result-type">
                          판정 사고 유형
                        </span>
                      </div>

                      <h4>
                        차선 변경 중 접촉 사고
                      </h4>
                    </div>

                    <div>
                      <span className="small-label">
                        상황 요약
                      </span>

                      <p className="situation-summary">
                        직진 차로를 정상
                        주행 중인 내 차량
                        측면으로 상대 차량이
                        방향지시등 미점등
                        상태에서 진입하여
                        발생한 접촉 사고
                      </p>
                    </div>

                    <div className="fault-result">
                      <div className="fault-numbers">
                        <div>
                          <span>
                            내 과실
                          </span>

                          <strong className="my-fault">
                            20%
                          </strong>
                        </div>

                        <div className="fault-center">
                          <strong>VS</strong>

                          <span>
                            충돌 직전 차선
                            침범 감지
                          </span>
                        </div>

                        <div>
                          <span>
                            상대방 과실
                          </span>

                          <strong className="other-fault">
                            80%
                          </strong>
                        </div>
                      </div>

                      <div className="fault-bar">
                        <div className="fault-bar-me" />
                        <div className="fault-bar-other" />
                      </div>

                      <div className="fault-tags">
                        <span>
                          기본 30:70
                        </span>

                        <span className="blue-tag">
                          깜빡이 미점등
                        </span>

                        <span>
                          직진 우선권 인정
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="result-buttons">
                    <button
                      type="button"
                      className="secondary-action"
                      onClick={() =>
                        setStage(
                          "reanalysis"
                        )
                      }
                    >
                      <span className="material-symbols-outlined">
                        replay
                      </span>

                      사고 상황이 일치하지
                      않습니다
                    </button>

                    <button
                      type="button"
                      className="modal-primary-button"
                      onClick={() => {
                        setModalOpen(false);
                        navigate("/report");
                      }}
                    >
                      사고 상황이 일치합니다

                      <span className="material-symbols-outlined">
                        arrow_forward
                      </span>
                    </button>
                  </div>
                </div>
              )}

              {/* ======================================
                  재분석
              ====================================== */}

              {stage ===
                "reanalysis" && (
                <div className="modal-stage">
                  <div>
                    <h3>
                      AI 재분석 요청 사유
                      선택
                    </h3>

                    <p className="modal-description">
                      실제 사고 상황과 다른
                      항목을 선택해 주세요.
                    </p>
                  </div>

                  <div className="reanalyze-options">
                    <ReanalyzeOption
                      value="not_lane_change"
                      checked={
                        reanalyzeReason ===
                        "not_lane_change"
                      }
                      onChange={() =>
                        setReanalyzeReason(
                          "not_lane_change"
                        )
                      }
                      title="차선 변경 사고가 아님"
                      description="교차로 직진·좌회전 또는 다른 사고 유형입니다."
                    />

                    <ReanalyzeOption
                      value="signal_violation"
                      checked={
                        reanalyzeReason ===
                        "signal_violation"
                      }
                      onChange={() =>
                        setReanalyzeReason(
                          "signal_violation"
                        )
                      }
                      title="신호위반 또는 중과실 요소 존재"
                      description="신호위반, 중앙선 침범 등의 상황이 있습니다."
                    />

                    <ReanalyzeOption
                      value="vehicle_priority"
                      checked={
                        reanalyzeReason ===
                        "vehicle_priority"
                      }
                      onChange={() =>
                        setReanalyzeReason(
                          "vehicle_priority"
                        )
                      }
                      title="통행 우선권 오인식"
                      description="내 차량의 선진입 상황이 잘못 인식되었습니다."
                    />
                  </div>

                  <div className="reanalyze-buttons">
                    <button
                      type="button"
                      className="back-button"
                      onClick={() =>
                        setStage(
                          "resultSummary"
                        )
                      }
                    >
                      ← 이전으로 돌아가기
                    </button>

                    <button
                      type="button"
                      className="modal-primary-button"
                      onClick={() => startAnalysis("resultSummary", true)}
                    >
                      <span className="material-symbols-outlined">
                        auto_fix_high
                      </span>

                      재분석
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ======================================================
   COMPONENTS
====================================================== */

function GuideItem({
  number,
  title,
  children,
}) {
  return (
    <div className="guide-item">
      <div className="guide-number">
        {number}
      </div>

      <div>
        <strong>
          {title}
        </strong>

        <p>
          {children}
        </p>
      </div>
    </div>
  );
}

function StepIndicator({ current }) {
  return (
    <div className="step-indicator">
      {[1, 2, 3, 4].map(
        (number, index) => (
          <div
            className="step-wrapper"
            key={number}
          >
            <span
              className={`step-badge ${
                current === number
                  ? "step-active"
                  : current > number
                    ? "step-complete"
                    : ""
              }`}
            >
              {number}.{" "}
              {
                [
                  "동의",
                  "분석",
                  "질문",
                  "상황 결과",
                ][index]
              }
            </span>

            {number !== 4 && (
              <span className="step-arrow">
                ›
              </span>
            )}
          </div>
        )
      )}
    </div>
  );
}

function QuestionCard({
  number,
  question,
  children,
}) {
  return (
    <div className="question-card">
      <strong className="question-title">
        <span>
          {number}
        </span>

        {question}
      </strong>

      <div className="radio-grid">
        {children}
      </div>
    </div>
  );
}

function RadioOption({
  name,
  checked,
  onChange,
  label,
}) {
  return (
    <label
      className={`radio-option ${
        checked ? "radio-selected" : ""
      }`}
    >
      <input
        type="radio"
        name={name}
        checked={checked}
        onChange={onChange}
      />

      <span>
        {label}
      </span>
    </label>
  );
}

function Milestone({
  number,
  text,
  done,
}) {
  return (
    <div
      className={`milestone ${
        done ? "milestone-done" : ""
      }`}
    >
      <div>
        <span className="material-symbols-outlined">
          {done
            ? "check_circle"
            : "schedule"}
        </span>

        <span>
          {number}. {text}
        </span>
      </div>

      <span className="milestone-status">
        {done ? "완료" : "대기"}
      </span>
    </div>
  );
}

function ReanalyzeOption({
  checked,
  onChange,
  title,
  description,
}) {
  return (
    <label
      className={`reanalyze-option ${
        checked
          ? "reanalyze-selected"
          : ""
      }`}
    >
      <input
        type="radio"
        name="reanalyze"
        checked={checked}
        onChange={onChange}
      />

      <div>
        <strong>
          {title}
        </strong>

        <p>
          {description}
        </p>
      </div>
    </label>
  );
}

export default Home;