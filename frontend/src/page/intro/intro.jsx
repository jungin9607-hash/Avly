import { useState } from "react";
import { useNavigate } from "react-router-dom";
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
            {/* Logo */}
            <a href="#" className="brand">
              <img
                className="brand-logo"
                src="https://lh3.googleusercontent.com/aida/AEtjO1WmxxhaY118czpIAPP1dWqPRkqg9lI_4b37P_Ih2NexVXTvNcZZxbt3VRAa4QUY4puYIjPE5kC18qK2wzxRM_L-cEi8JjEqxJN98d73zx_VjyqdGr-oh3pQIMUL3zVOnRmKiT3PWkOKjHxEbkhkb6EaFZ-U0KxrvrXwaorCjR4k8-JJEdw1n7NfGUZzgF7msnwNL0wA3XA--mgmt3KNQ_3tXbFIXSn_R84u-zeR93UrRJ0sqYGoJspHcWdb2Iyq1mYe8jyxImhIKTo"
                alt="Avly"
              />

              <div className="brand-text">
                <span className="brand-name">Avly</span>
                <span className="brand-korean">에블리</span>

                <span className="brand-divider">|</span>

                <span className="brand-description">
                  AI 교통사고 과실 분석
                </span>
              </div>
            </a>

            {/* Navigation */}
            <nav className="navigation" aria-label="메인 메뉴">
              <a href="#" className="nav-item nav-active">
                홈
              </a>

              <a href="#" className="nav-item">
                분석 결과
              </a>

              <div className="nav-item-group">
                <a href="#" className="nav-item nav-trigger">
                  사고 분석
                </a>

                <div className="mega-menu" aria-label="사고 분석 메뉴">
                  <a href="#" className="mega-menu-item">
                    사고 순간 타임라인
                  </a>
                  <a href="#" className="mega-menu-item">
                    유사 판례 분석
                  </a>
                </div>
              </div>

              <a href="#" className="nav-item">
                사고 예방
              </a>
            </nav>
          </div>

          {/* Header Right */}
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
                <a href="#" className="mobile-menu-brand">
                  <img className="brand-logo" src="https://lh3.googleusercontent.com/aida/AEtjO1WmxxhaY118czpIAPP1dWqPRkqg9lI_4b37P_Ih2NexVXTvNcZZxbt3VRAa4QUY4puYIjPE5kC18qK2wzxRM_L-cEi8JjEqxJN98d73zx_VjyqdGr-oh3pQIMUL3zVOnRmKiT3PWkOKjHxEbkhkb6EaFZ-U0KxrvrXwaorCjR4k8-JJEdw1n7NfGUZzgF7msnwNL0wA3XA--mgmt3KNQ_3tXbFIXSn_R84u-zeR93UrRJ0sqYGoJspHcWdb2Iyq1mYe8jyxImhIKTo" alt="" />
                  <span><strong>Avly</strong> <small>교통사고 AI 분석</small></span>
                </a>
                <button type="button" className="mobile-menu-close" aria-label="메뉴 닫기" onClick={() => setMobileMenuOpen(false)}>
                  <span className="material-symbols-outlined">close</span>
                </button>
              </div>
              <nav className="mobile-menu-list">
                <a href="#" className="mobile-menu-item active" onClick={() => setMobileMenuOpen(false)}>
                  <span className="material-symbols-outlined">home</span><span>홈</span>
                  <small className="mobile-menu-current">현재 화면</small>
                </a>
                <a href="#" className="mobile-menu-item" onClick={() => setMobileMenuOpen(false)}>
                  <span className="material-symbols-outlined">analytics</span><span>분석 결과</span>
                </a>
                <button type="button" className="mobile-menu-item mobile-menu-analysis" aria-expanded={mobileAnalysisOpen} onClick={() => setMobileAnalysisOpen((open) => !open)}>
                  <span className="material-symbols-outlined">error_outline</span><span>사고 분석</span><span className="material-symbols-outlined mobile-menu-chevron">expand_more</span>
                </button>
                {mobileAnalysisOpen && (
                  <div className="mobile-submenu">
                    <a href="#" onClick={() => setMobileMenuOpen(false)}><span>사고 순간 타임라인</span><small>보기 &gt;</small></a>
                    <a href="#" onClick={() => setMobileMenuOpen(false)}><span>유사 판례 분석</span><small>보기 &gt;</small></a>
                  </div>
                )}
                <a href="#" className="mobile-menu-item" onClick={() => setMobileMenuOpen(false)}>
                  <span className="material-symbols-outlined">verified_user</span><span>사고 예방</span>
                </a>
              </nav>
            </aside>
          </div>
        )}
      </header>

      {/* ================= MAIN ================= */}
      <main className="main">
        <section className="intro-section">

          {/* Background Decoration */}
          <div className="intro-background">
            <div className="intro-gradient-circle intro-circle-right"></div>
            <div className="intro-gradient-circle intro-circle-left"></div>
          </div>

          <div className="intro-container">
            <div className="intro-grid">

              {/* LEFT */}
              <div className="intro-content">

                <div className="intro-badge">
                  <span className="badge-dot"></span>

                  <span className="badge-title">
                    A PIECE OF TRUTH · AVLY
                  </span>

                  <span className="badge-divider">·</span>

                  <span className="badge-description">
                    대법원 판례 기반 검증 엔진
                  </span>
                </div>

                <h1 className="intro-title">
                  불안했던 사고의 순간,
                  <br />
                  <span className="intro-highlight">
                    명확한 진실
                  </span>
                  을 기억하는 방법
                </h1>

                <p className="intro-description">
                  에블리는 단순한 과실 비율 숫자만 던지지 않습니다.
                  <br />

                  <strong>
                    왜 그런 과실이 도출되었는지
                  </strong>{" "}

                  3천여 개 대법원 판례와 손해보험협회 인정기준으로
                  명쾌하게 입증합니다.
                </p>

                <button
  type="button"
  className="analysis-button"
  onClick={() => navigate("/home")}
>
  <span className="material-symbols-outlined">
    videocam
  </span>

  <span>블랙박스 영상 분석하러가기</span>

  <span className="material-symbols-outlined arrow-icon">
    arrow_forward
  </span>
</button>
              </div>

              {/* RIGHT */}
              <div className="engine-area">
                <div className="engine-wrapper">
                  <div className="engine-glow"></div>

                  <div className="engine-card">

                    {/* Card Header */}
                    <div className="engine-header">

                      <div className="window-buttons">
                        <span className="window-dot red"></span>
                        <span className="window-dot gray"></span>
                        <span className="window-dot green"></span>
                      </div>

                      <div className="engine-version">
                        <span className="material-symbols-outlined">
                          smart_toy
                        </span>

                        <span>에블리 2.4 엔진</span>
                      </div>
                    </div>

                    {/* Character */}
                    <div className="mascot-area">
                      <img
                        className="mascot-image"
                        src="https://lh3.googleusercontent.com/aida/AEtjO1VIUd6fpFekUSrsnTthFTL5z1AKhNaJszhvb_CeTmp7X68Q0pJXWSSq6FafQfBsI7-DC60GcyL5vFgWj0_RTkg0QKfTY7OpKVRt1KmqlmmycuZHdAamui88kgh1aN1ZKl7z0XxWmhlUSqME2yFumwCOQ3j2pKzIfIXb4Sic0P8NaXCFbweThlBOSMbbBNIfxVWkrJhK6s-F51r_75m4LtgX41r5ZJbp0a0qImql5EUh4nWRMmCHjxT41549"
                        alt="Avly AI 캐릭터"
                      />
                    </div>

                    {/* Engine Status */}
                    <div className="engine-status-list">

                      <div className="engine-status-item">
                        <div className="status-name">
                          <span className="material-symbols-outlined blue">
                            verified
                          </span>

                          <span>대법원 판례 빅데이터 매칭</span>
                        </div>

                        <strong className="blue">
                          실시간 동기화
                        </strong>
                      </div>

                      <div className="engine-status-item">
                        <div className="status-name">
                          <span className="material-symbols-outlined green-text">
                            speed
                          </span>

                          <span>초정밀 모션 텔레메트리</span>
                        </div>

                        <strong className="green-text">
                          98.4% 정확도
                        </strong>
                      </div>

                    </div>
                  </div>

                  {/* Floating Card 1 */}
                  <div className="floating-card floating-left">
                    <div className="floating-icon blue-background">
                      <span className="material-symbols-outlined">
                        shield
                      </span>
                    </div>

                    <div>
                      <strong>손보협회 252호 연계</strong>
                      <p>공식 과실인정 도표 대조</p>
                    </div>
                  </div>

                  {/* Floating Card 2 */}
                  <div className="floating-card floating-right">
                    <div className="floating-icon green-background">
                      <span className="material-symbols-outlined">
                        gavel
                      </span>
                    </div>

                    <strong>분심위 승소 사례 탑재</strong>
                  </div>

                </div>
              </div>
            </div>

            {/* ================= FEATURE CARDS ================= */}
            <section className="features">

              {/* Card 1 */}
              <article className="feature-card">
                <div>
                  <div className="feature-icon blue-background">
                    <span className="material-symbols-outlined">
                      videocam
                    </span>
                  </div>

                  <h3>블랙박스 영상 AI 분석</h3>

                  <p className="feature-description">
                    초단위 객체 탐지 및 모션 텔레메트리로 충돌 전후
                    찰나의 순간, 방향지시등 점등 여부와 차선 침범
                    각도를 정밀 분석합니다.
                  </p>
                </div>

                <div className="feature-detail">
                  <div className="feature-detail-row">
                    <span>초단위 객체 탐지 추출</span>

                    <strong className="blue">
                      99.2% 인식률
                    </strong>
                  </div>

                  <div className="progress">
                    <div className="progress-blue"></div>
                  </div>

                  <div className="feature-check">
                    <span className="material-symbols-outlined blue">
                      check_circle
                    </span>

                    <span>
                      초정밀 프레임 복원 & 객체 트래킹
                    </span>
                  </div>
                </div>
              </article>

              {/* Card 2 */}
              <article className="feature-card">
                <div>
                  <div className="feature-icon dark-background">
                    <span className="material-symbols-outlined">
                      percent
                    </span>
                  </div>

                  <h3>AI 예상과실 비율 제시</h3>

                  <p className="feature-description">
                    손해보험협회 과실비율 인정기준 252개 도표와 AI
                    비전 감정 결과를 대조하여 합리적이고 객관적인 예상
                    과실비율을 투명하게 산출합니다.
                  </p>
                </div>

                <div className="feature-detail">
                  <div className="feature-detail-row">
                    <strong>손보협회 기준 252호 대조</strong>

                    <strong className="blue">
                      20 : 80
                    </strong>
                  </div>

                  <div className="fault-ratio-bar">
                    <div className="fault-user"></div>
                    <div className="fault-opponent"></div>
                  </div>

                  <p className="feature-small-text">
                    기본 30:70 대비 감산 요인 반영 20:80
                  </p>
                </div>
              </article>

              {/* Card 3 */}
              <article className="feature-card">
                <div>
                  <div className="feature-icon green-background">
                    <span className="material-symbols-outlined">
                      balance
                    </span>
                  </div>

                  <h3>유사 판례와 비교</h3>

                  <p className="feature-description">
                    대법원 및 하급심 교통사고 판례 빅데이터와
                    1:1 매칭하여 내 사고와 가장 유사한 판례의 쟁점과
                    판결 결과를 비교 분석합니다.
                  </p>
                </div>

                <div className="feature-detail precedent-list">

                  <div className="feature-check">
                    <span className="material-symbols-outlined green-text">
                      task_alt
                    </span>

                    <span>
                      유사도 98% 판례 매칭 · 판결 요지 비교
                    </span>
                  </div>

                  <div className="feature-check">
                    <span className="material-symbols-outlined green-text">
                      task_alt
                    </span>

                    <span>
                      대법원·하급심 주요 쟁점 조항 요약
                    </span>
                  </div>

                  <div className="feature-check">
                    <span className="material-symbols-outlined green-text">
                      task_alt
                    </span>

                    <span>
                      소송 및 분쟁조정 사전 승소율 검증
                    </span>
                  </div>

                </div>
              </article>

            </section>
          </div>
        </section>
      </main>

      {/* ================= FOOTER ================= */}
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