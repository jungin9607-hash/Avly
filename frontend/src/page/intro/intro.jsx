import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import avlyBrand from "../../assets/avly-brand.png";
import avlyCharacterWordmark from "../../assets/avly-character-wordmark-transparent.png";
import avlyMascot from "../../assets/avly-mascot.png";
import "./intro.css";

function Intro() {
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileAnalysisOpen, setMobileAnalysisOpen] = useState(true);

  return (
    <div className="home-page">
      {/* ================= HEADER ================= */}
      <header className="header">
        <div className="header-inner">
          <div className="header-left">
            <Link to="/" className="brand">
              <img
                className="brand-logo brand-header-logo"
                src={avlyBrand}
                alt="에블리 캐릭터와 로고"
              />

              <div className="brand-text">
                <span className="brand-name">Avly</span>
                <span className="brand-korean">에블리</span>

                <span className="brand-divider">|</span>

                <span className="brand-description">
                  AI 교통사고 과실 분석
                </span>
              </div>
            </Link>

            <nav className="navigation" aria-label="메인 메뉴">
              <Link to="/home" className="nav-item nav-active">
                홈
              </Link>

              <Link to="/report" className="nav-item">
                분석 결과
              </Link>

              <div className="nav-item-group">
                <button type="button" className="nav-item nav-trigger" aria-haspopup="true">
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

              <Link to="/home" className="nav-item">
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
                  <button type="button" className="mobile-menu-item mobile-menu-analysis" aria-expanded={mobileAnalysisOpen} aria-controls="intro-analysis-submenu" onClick={() => setMobileAnalysisOpen((open) => !open)}>
                    <span className="material-symbols-outlined">error_outline</span><span>사고 분석</span><span className="material-symbols-outlined">expand_more</span>
                  </button>
                </div>
                {mobileAnalysisOpen && (
                  <div className="mobile-submenu" id="intro-analysis-submenu">
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

      <main className="main">
        <section className="intro-section">
          <div className="intro-background">
            <div className="intro-gradient-circle intro-circle-right"></div>
            <div className="intro-gradient-circle intro-circle-left"></div>
          </div>

          <div className="intro-container">
            <div className="intro-grid">

              <div className="intro-content">
                <h1 className="intro-title">
                  사고는 한순간,
                  <br />
                  <span className="intro-highlight">판단</span>
                  에는 이유가 있습니다
                </h1>
                <p className="intro-description">
                  에블리는 단순한 과실 비율 숫자만 던지지 않습니다.
                  <br />
                  <strong>과실비율의 근거</strong>까지 설명합니다.
                </p>
                <button type="button" className="analysis-button" onClick={() => navigate("/home")}>
                  <span className="material-symbols-outlined">videocam</span>
                  <span>블랙박스 영상 분석하러가기</span>
                  <span className="material-symbols-outlined arrow-icon">arrow_forward</span>
                </button>
              </div>

              <div className="engine-area">
                <div className="engine-wrapper">
                  <img
                    className="mascot-image"
                    src={avlyCharacterWordmark}
                    alt="에블리 캐릭터와 큰 로고 글자"
                  />
                </div>
              </div>
            </div>

            <section className="features">
              <article className="feature-card">
                <div className="feature-heading">
                  <div className="feature-icon blue-background">
                    <span className="material-symbols-outlined">videocam</span>
                  </div>
                  <h3>블랙박스 영상 AI 분석</h3>
                </div>
                <div className="feature-detail">
                  <div className="feature-detail-row">
                    <span>초단위 객체 탐지 추출</span>
                    <strong className="blue">99.2% 인식률</strong>
                  </div>
                  <div className="progress"><div className="progress-blue" /></div>
                  <div className="feature-check">
                    <span className="material-symbols-outlined blue">check_circle</span>
                    <span>초정밀 프레임 복원 & 객체 트래킹</span>
                  </div>
                </div>
              </article>
              <article className="feature-card">
                <div className="feature-heading">
                  <div className="feature-icon dark-background">
                    <span className="material-symbols-outlined">percent</span>
                  </div>
                  <h3>예상 과실비율 및 판단 근거</h3>
                </div>
                <div className="feature-detail">
                  <div className="feature-detail-row">
                    <strong>손보협회 기준 252호 대조</strong>
                    <strong className="blue">20 : 80</strong>
                  </div>
                  <div className="fault-ratio-bar">
                    <div className="fault-user" />
                    <div className="fault-opponent" />
                  </div>
                  <p className="feature-small-text">기본 30:70 대비 감산 요인 반영 20:80</p>
                </div>
              </article>
              <article className="feature-card">
                <div className="feature-heading">
                  <div className="feature-icon green-background">
                    <span className="material-symbols-outlined">balance</span>
                  </div>
                  <h3>유사 사고 기준 및 판례</h3>
                </div>
                <div className="feature-detail precedent-list">
                  <div className="feature-check">
                    <span className="material-symbols-outlined green-text">task_alt</span>
                    <span>유사도 98% 판례 매칭 · 판결 요지 비교</span>
                  </div>
                  <div className="feature-check">
                    <span className="material-symbols-outlined green-text">task_alt</span>
                    <span>대법원·하급심 주요 쟁점 조항 요약</span>
                  </div>
                  <div className="feature-check">
                    <span className="material-symbols-outlined green-text">task_alt</span>
                    <span>소송 및 분쟁조정 사전 승소율 검증</span>
                  </div>
                </div>
              </article>
            </section>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="footer-inner">
          <div className="legal-notice">
            <div className="legal-left">
              <span className="material-symbols-outlined blue legal-icon">
                verified_user
              </span>
              <div>
                <h4>법적 책임 고지 및 안내</h4>
                <p>
                  본 서비스는 AI 영상 분석 엔진 및 대법원·손해보험협회
                  과실비율 인정기준 판례 데이터를 기반으로 제공되는
                  객관적 참고자료이며, 변호사법 제109조에 따른 법률적
                  대리 행위 또는 확정 판결을 대신하지 않습니다.
                </p>
              </div>
            </div>

            <button type="button" className="guideline-button">
              판례 기준 가이드라인
            </button>
          </div>

          <div className="footer-bottom">
            <div className="footer-links">
              <div className="footer-brand">
                <strong>Avly</strong>
                <span>(에블리)</span>
              </div>

              <span>·</span>

              <a href="#">이용약관</a>

              <span>·</span>

              <a href="#" className="footer-strong">
                개인정보처리방침
              </a>

              <span>·</span>

              <a href="#">고객지원센터</a>
            </div>
            <p className="copyright">
              © 2025 Avly Inc. All rights reserved.
            </p>

          </div>
        </div>
      </footer>
    </div>
  );
}

export default Intro;