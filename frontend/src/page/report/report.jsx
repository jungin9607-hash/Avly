import { useState } from "react";
import { Link } from "react-router-dom";
import avlyBrand from "../../assets/avly-brand.png";
import avlyMascot from "../../assets/avly-mascot.png";
import "./report.css";

function Report() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileAnalysisOpen, setMobileAnalysisOpen] = useState(true);
  const [shareOpen, setShareOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [toast, setToast] = useState("");

  const showToast = (message) => {
    setToast(message);

    setTimeout(() => {
      setToast("");
    }, 3000);
  };

  const handleDownload = () => {
    showToast("과실분석 종합 리포트(PDF)를 다운로드합니다.");
  };

  const handleShareSubmit = (e) => {
    e.preventDefault();

    setShareOpen(false);
    showToast(`${email} 주소로 분석 리포트를 성공적으로 발송했습니다.`);
    setEmail("");
  };

  return (
    <div className="report-page">
      {/* HEADER */}
      <header className="report-header">
        <div className="report-header-inner">
          <div className="report-header-left">
            <Link className="report-brand-link" to="/">
              <img
                className="report-brand-logo"
                src={avlyBrand}
                alt="에블리 캐릭터와 로고"
              />
              <span className="report-brand-name">Avly</span>
              <span className="report-brand-korean">에블리</span>
              <span className="report-brand-divider">|</span>
              <span className="report-brand-description">AI 교통사고 과실 분석</span>
            </Link>

            <nav className="report-nav" aria-label="메인 메뉴">
              <Link className="report-nav-item" to="/home">홈</Link>
              <Link className="report-nav-item active" to="/report">분석 결과</Link>
              <div className="report-nav-group">
                <button type="button" className="report-nav-item" aria-haspopup="true">사고 분석</button>
                <div className="report-mega-menu" aria-label="사고 분석 메뉴">
                  <Link to="/time">사고 순간 타임라인</Link>
                  <Link to="/law">유사 판례 분석</Link>
                </div>
              </div>
              <Link className="report-nav-item" to="/home">사고 예방</Link>
            </nav>
          </div>

          <div className="report-header-actions">
            <button
              type="button"
              className="report-menu-toggle"
              aria-label="메뉴 열기"
              aria-expanded={mobileMenuOpen}
              onClick={() => setMobileMenuOpen((open) => !open)}
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
                  <img className="report-drawer-logo" src={avlyMascot} alt="" />
                  <span><strong>Avly</strong> <small>교통사고 AI 분석</small></span>
                </Link>
                <button type="button" className="mobile-menu-close" aria-label="메뉴 닫기" onClick={() => setMobileMenuOpen(false)}>
                  <span className="material-symbols-outlined">close</span>
                </button>
              </div>
              <nav className="mobile-menu-list">
                <Link to="/home" className="mobile-menu-item" onClick={() => setMobileMenuOpen(false)}>
                  <span className="material-symbols-outlined">home</span><span>홈</span>
                </Link>
                <Link to="/report" className="mobile-menu-item active" onClick={() => setMobileMenuOpen(false)}>
                  <span className="material-symbols-outlined">analytics</span><span>분석 결과</span>
                  <small className="mobile-menu-current">현재 화면</small>
                </Link>
                <div className="mobile-menu-analysis-row">
                  <button type="button" className="mobile-menu-item mobile-menu-analysis" aria-expanded={mobileAnalysisOpen} aria-controls="report-analysis-submenu" onClick={() => setMobileAnalysisOpen((open) => !open)}>
                    <span className="material-symbols-outlined">error_outline</span><span>사고 분석</span><span className="material-symbols-outlined">expand_more</span>
                  </button>
                </div>
                {mobileAnalysisOpen && (
                  <div className="mobile-submenu" id="report-analysis-submenu">
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

      {/* MAIN */}
      <main className="report-main">
        <div className="report-container">
          {/* 분석 정보 상단 */}
          <section className="report-summary-header">
            <div className="summary-info">
              <div className="summary-code">
                <span>식별 코드</span>
                <strong>AV-24901</strong>
              </div>

              <div className="summary-divider" />

              <div className="summary-type">
                <span className="material-symbols-outlined">alt_route</span>
                <strong>사고 유형: 차선 변경 중 접촉 사고</strong>
              </div>
            </div>

          </section>

          <div className="report-grid">
            {/* LEFT */}
            <div className="report-left">
              {/* 과실비율 */}
              <section className="report-card fault-card">
                <div className="card-title-row">
                  <div className="card-title">
                    <span className="material-symbols-outlined">balance</span>
                    <h2>과실 비율 최종 산정치</h2>
                  </div>
                </div>

                <div className="fault-ratio-box">
                  <div className="fault-ratio-top">
                    <div className="fault-owner">
                      <span className="ratio-dot blue" />
                      <span className="ratio-name">내 과실</span>
                      <strong className="ratio-number blue-text">20%</strong>
                    </div>

                    <div className="fault-owner">
                      <strong className="ratio-number red-text">80%</strong>
                      <span className="ratio-name">상대 과실</span>
                      <span className="ratio-dot red" />
                    </div>
                  </div>

                  <div className="ratio-bar">
                    <div className="ratio-my">20%</div>
                    <div className="ratio-gap" />
                    <div className="ratio-other">80%</div>
                  </div>

                  <div className="discount-box">
                    <span className="material-symbols-outlined">
                      trending_down
                    </span>

                    <span>
                      기본 과실(30%) 대비{" "}
                      <strong>10%p 감산 인정</strong>
                      {" "}(내 과실 절감 요건 입증 완료)
                    </span>
                  </div>
                </div>

                {/* 분석 이유 */}
                <div className="reason-section">
                  <div className="reason-title">
                    <h3>왜 20:80으로 분석됐나요?</h3>
                    <span>단계별 과실 조정 요인</span>
                  </div>

                  <div className="reason-list">
                    <div className="reason-item">
                      <div className="reason-number">1</div>

                      <div className="reason-content">
                        <div className="reason-header">
                          <strong>표준 과실 기준 (30:70)</strong>
                          <span>기본율 적용</span>
                        </div>

                        <p>
                          동일 방향 진행 중 진로 변경 사고의 표준 과실
                          기본도표(제252호)에 따라 피변경 차량 30%,
                          진로변경 차량 70%를 기준값으로 시작합니다.
                        </p>
                      </div>
                    </div>

                    <div className="reason-item">
                      <div className="reason-number highlight">2</div>

                      <div className="reason-content">
                        <div className="reason-header">
                          <strong>상대측 신호 미표시 (-5%p)</strong>
                          <span className="blue-badge">-5%p 감산</span>
                        </div>

                        <p>
                          진로변경 30m 전 방향지시등을 점등하지 않은 상대
                          차량의 명백한 도로교통법 제38조 위반이 영상
                          분초 단위(24.3초)로 확인되었습니다.
                        </p>
                      </div>
                    </div>

                    <div className="reason-item">
                      <div className="reason-number highlight">3</div>

                      <div className="reason-content">
                        <div className="reason-header">
                          <strong>근접 급진입 및 불가항력 (-5%p)</strong>
                          <span className="blue-badge">-5%p 추가 감산</span>
                        </div>

                        <p>
                          안전거리 미확보 상태에서 차간 4.2m로
                          진입하였으며, 인지반응시간(0.8초) 내 충돌
                          회피가 물리적으로 불가능했음이 텔레메트리로
                          검증되었습니다.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </section>

              {/* 속도 / TTC / 반응시간 */}
              <section className="telemetry-card">
                <div className="telemetry-item">
                  <div className="telemetry-icon">
                    <span className="material-symbols-outlined">speed</span>
                  </div>

                  <div>
                    <p>충돌 1.5초 전 내 속도</p>
                    <strong>
                      46 km/h
                      <small className="safe">
                        제한속도 50km/h 내
                      </small>
                    </strong>
                  </div>
                </div>

                <div className="telemetry-item">
                  <div className="telemetry-icon danger">
                    <span className="material-symbols-outlined">timer</span>
                  </div>

                  <div>
                    <p>충돌여유시간 (TTC)</p>
                    <strong>
                      0.72 초
                      <small className="danger-text">
                        회피 한계 도달
                      </small>
                    </strong>
                  </div>
                </div>

                <div className="telemetry-item">
                  <div className="telemetry-icon">
                    <span className="material-symbols-outlined">
                      airline_stops
                    </span>
                  </div>

                  <div>
                    <p>제동 반응 시간</p>
                    <strong>
                      0.31 초
                      <small className="safe">
                        즉각 브레이크 작동
                      </small>
                    </strong>
                  </div>
                </div>
              </section>
            </div>

            {/* RIGHT */}
            <div className="report-right">
              <section className="report-card evidence-card">
                <div className="card-title-row">
                  <div className="card-title">
                    <span className="material-symbols-outlined">policy</span>
                    <h2>과실 산정 핵심 증거</h2>
                  </div>
                </div>

                <div className="evidence-list">
                  {/* 증거 1 */}
                  <div className="evidence-item">
                    <div className="evidence-heading">
                      <span className="material-symbols-outlined check">
                        check_circle
                      </span>

                      <div className="evidence-content">
                        <div className="evidence-title">
                          <strong>상대 차량 방향지시등 미점등</strong>
                          <span className="red-badge">99.8% 미동작</span>
                        </div>

                        <p>
                          진입 전 3개 연속 프레임(초당 30fps) 픽셀 조도
                          추적 결과 방향지시등 비활성 상태가 정밀
                          입증되었습니다.
                        </p>
                      </div>
                    </div>

                    <div className="evidence-images">
                      <div className="evidence-image">
                        <img
                          src="https://lh3.googleusercontent.com/aida-public/AB6AXuDyFN-05PM9yPQEbJUu5ievvfxLz8gy_hViKmNIOd0GjsDSWf83KCHmQhOXyik1VEtzPtbN_f6omzwfEcHw99RDRMQR2AT_S13ZTT7qCT_e6fGx2rCl7O6ncuQt2LteSxtLJSoj591KrbiLLscQRXx4j4_h-jvtAV6GgMhhOM2Yo7Q2AjabucLzbLp5-Drq7ryw0pyPvbhV-xRkmsUbp89e6O63G2RYmmCd3IDdTxLecHxJDc4jMvKtbQ"
                          alt="사고 증거 1"
                        />
                        <span>00:23.8</span>
                      </div>

                      <div className="evidence-image">
                        <img
                          src="https://lh3.googleusercontent.com/aida-public/AB6AXuAtjtEhlS-EpPWbP6dvXoSBo9A8RHK_wCUkidqq3svDWGyAzu-h6KFQf42BOo9uKoVsW453na31QcwtaAdIkZ2bt909JONKGa6OAhkpyYDdDR1Bs2rvadZHzRmK5YwFf5Z4WHE0nDM5c6WOFcgHQks8orudneWXY2_qDDjfQnlYEyTs3n6d0_5zTeXtLekyM0PlSGOzCMvSr_TnSmMHs4F9G0C3Zm--CKem5EQg2N-UF5fJbGU0dXsi4A"
                          alt="사고 증거 2"
                        />
                        <span>00:24.1</span>
                      </div>

                      <div className="evidence-image">
                        <img
                          src="https://lh3.googleusercontent.com/aida-public/AB6AXuB52Ur2821Rqxas0JWQ9pqOJHYzz1hUl7y2CO38vN2nfS377n-fZKCGcjHSrrJDvq5zn1ReBGzjfibhdlOMn2y-eXOREKmlNENH0k3qwoF27CriqHVAWxwVCMTXX3fQXntmNcDQOF8y-xzm5OtaoUSpueq269KoTgYMyZOIRWk-4C6_Zs23UzLWHUwvl9S60N3_asAAXTH1QNnziOHkSoKmF6LNPtTsOxTeKanpqcxzotySW8MW4UPC0A"
                          alt="사고 증거 3"
                        />
                        <span>00:24.5</span>
                      </div>
                    </div>
                  </div>

                  {/* 증거 2 */}
                  <div className="evidence-item simple">
                    <span className="material-symbols-outlined check">
                      check_circle
                    </span>

                    <div className="evidence-content">
                      <div className="evidence-title">
                        <strong>규정속도 준수 및 직진 차선 유지</strong>
                        <span className="green-badge">46km/h 준수</span>
                      </div>

                      <p>
                        GPS 센서 데이터 및 도로 차선 간격 분석 결과,
                        내 차량은 제한속도(50km/h) 이하로 2차로 중심선
                        정중앙을 유지하고 있었습니다.
                      </p>

                      <div className="evidence-detail">
                        <span className="material-symbols-outlined">
                          gps_fixed
                        </span>
                        차로 이탈률 0.04m 이내 (안정적 직진 주행 완료)
                      </div>
                    </div>
                  </div>

                  {/* 증거 3 */}
                  <div className="evidence-item simple">
                    <span className="material-symbols-outlined check">
                      check_circle
                    </span>

                    <div className="evidence-content">
                      <div className="evidence-title">
                        <strong>무리한 급진입 및 제동 불가항력</strong>
                        <span className="red-outline-badge">TTC 0.72초</span>
                      </div>

                      <p>
                        인간 운전자의 평균 제동 인지 반응 시간
                        (0.7초~1.0초)을 밑도는 시점에 급격히 유입되어
                        충돌 회피 기회가 물리적으로 결여되었습니다.
                      </p>

                      <div className="evidence-detail danger-text">
                        <span className="material-symbols-outlined">
                          gavel
                        </span>
                        대법원 2018다293282 '회피 불능 신뢰의 원칙' 부합
                      </div>
                    </div>
                  </div>
                </div>

                <div className="report-action-buttons">
                  <button
                    className="download-button"
                    onClick={handleDownload}
                  >
                    <span className="material-symbols-outlined">download</span>
                    PDF 다운로드
                  </button>

                  <button
                    className="share-button"
                    onClick={() => setShareOpen(true)}
                  >
                    <span className="material-symbols-outlined">share</span>
                    공유하기
                  </button>
                </div>
              </section>
            </div>
          </div>
        </div>
      </main>

      {/* FOOTER */}
      <footer className="report-footer">
        <div className="report-footer-inner">
          <div className="legal-notice">
            <span className="material-symbols-outlined">verified_user</span>

            <div>
              <strong>법적 책임 고지 및 안내</strong>

              <p>
                본 서비스는 AI 영상 분석 엔진 및 대법원·손해보험협회
                과실비율 인정기준 판례 데이터를 기반으로 제공되는
                참고자료이며 법률적 대리 행위 또는 확정 판결을
                대신하지 않습니다.
              </p>
            </div>
          </div>

          <div className="footer-bottom">
            <div>
              <strong>Avly</strong>
              <span> (에블리)</span>
            </div>

            <p>© 2026 Avly Inc. All rights reserved.</p>
          </div>
        </div>
      </footer>

      {/* 공유 모달 */}
      {shareOpen && (
        <div
          className="modal-overlay"
          onClick={() => setShareOpen(false)}
        >
          <div
            className="modal-container share-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <span className="material-symbols-outlined">send</span>
                <h3>분석 리포트 공유하기</h3>
              </div>

              <button onClick={() => setShareOpen(false)}>
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <form
              className="share-form"
              onSubmit={handleShareSubmit}
            >
              <label>
                이메일

                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="example@email.com"
                  required
                />
              </label>

              <div className="security-message">
                <span className="material-symbols-outlined">lock</span>
                보안 링크 및 암호화된 PDF 원본이 이메일로 발송됩니다.
              </div>

              <div className="share-form-buttons">
                <button
                  type="button"
                  className="cancel"
                  onClick={() => setShareOpen(false)}
                >
                  취소
                </button>

                <button type="submit" className="submit">
                  리포트 발송
                  <span className="material-symbols-outlined">
                    arrow_forward
                  </span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TOAST */}
      {toast && (
        <div className="report-toast">
          <span className="material-symbols-outlined">check_circle</span>
          {toast}
        </div>
      )}
    </div>
  );
}

export default Report;