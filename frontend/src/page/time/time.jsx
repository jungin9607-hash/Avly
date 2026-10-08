
import { useState } from "react";
import { Link } from "react-router-dom";
import avlyBrand from "../../assets/avly-brand.png";
import avlyMascot from "../../assets/avly-mascot.png";
import "./time.css";

const timelineData = [
  {
    id: "before5",
    step: "01",
    label: "충돌 5초 전",
    timestamp: "00:07.45",
    title: "본인 정상 주행 및 전방 안전거리 35m 확보",
    short: "정상 주행 & 거리 확보",
    status: "정상 주행권 인정",
    theme: "blue",
    image:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuA1xcjXO6_qbMaUY9Qs-bIE-3i4mc7Mr3Nur6UAIini1O0lwMum_MQg486CgZ56TUv3sAVBbGIp9ZUys_PRQ5_tP1IY-1IdQY6vOmnSxBCl_v9SJYC8vRrAapP5ve4V3dMsLnwCYzKFpLaza_fXuCGGInn5uC9T5kfNmYZw3FSytb4vQCuB1qidNBQgu9v-ceYI9uTyAG3217Euw_Bs9VXVQX8zFVZqyF_dZ3fuDvi_G_h0zlvJD_9LTg",
    overlay: "정속 주행 상태",
    telemetry: "CAM_FRONT",
    legalTag: "기본 과실 가산 요인 없음 (정상 주행)",
    explanation:
      "전방 주시 의무 및 안전거리 확보 규정(도로교통법 제19조)을 완벽히 준수하고 있었으며, 차선 내 정속 주행 상태로 자차 측의 선행 과실 원인이 전혀 존재하지 않습니다.",
    speedSelf: "48.0 km/h",
    speedOther: "51.2 km/h",
    distance: "35.2 m (안전)",
    yawRate: "0.0 deg/s",
    rangeVal: 74,
    scene: "본인 정상 주행 및 안전거리 35m 확보",
    legal: "전방주시태만 없음 입증 (도로교통법 준수)",
    impact: "손보협회 인정도표 제252호 기본 과실 (30:70) 출발",
  },
  {
    id: "before3",
    step: "02",
    label: "충돌 3초 전",
    timestamp: "00:09.12",
    title: "상대 차량 방향지시등(깜빡이) 미점등 급차선 변경 시작",
    short: "급차선변경 · 깜빡이 미점등",
    status: "★ 과실 가감산 결정적 요인",
    theme: "red",
    image:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuC-Rnm-hKgs5jGAAHbLDRhOJOpZHvNVI9O9YJXlUIsyO7DCrHL25lyh-g8Q6U761qbG13VleoWySQutxQVuaUF-OJOOgzz_K-5aDEcTOcftEJxK7cssEtEcYHBjCbSiVkEfcwQo22PK2Mi3AsFudMZ8KcF6r7mUOI1GMGmxziYCEdlblIdMrUFVQ81GSJbWOj0r_Y17e4NwCDfq1uEUmiBlFoc2IXKsBXmZUYLPULSuYtHR95BY6EJvYg",
    overlay: "도로교통법 제38조 위반",
    telemetry: "TELEMETRY_SPEED 46km/h",
    legalTag: "도로교통법 제38조 위반 (-10%p 감산)",
    explanation:
      "상대 차량 좌우 방향지시등 광도 센서 0.00% 인가. 도로교통법 제38조(차의 신호) 1항 위반 및 안전거리 미확보 급선회로 인해 기본 과실 30:70에서 상대방 과실 10%p 가중, 본인 과실 10%p 감산 적용됩니다.",
    speedSelf: "46.4 km/h",
    speedOther: "52.0 km/h",
    distance: "8.2 m (위험 진입)",
    yawRate: "24.3 deg/s",
    rangeVal: 91,
    scene: "상대 차량 방향지시등 미점등 급차선 변경",
    legal: "도로교통법 제38조(차의 신호) 위반 확증",
    impact: "내 과실 -10%p 감산 인정 (상대 +10%p 가산)",
  },
  {
    id: "before1",
    step: "03",
    label: "충돌 1초 전",
    timestamp: "00:10.85",
    title: "차간거리 3.4m 급감 및 긴급 제동 (방어운전 노력 입증)",
    short: "충돌 회피 한계 입증",
    status: "불가항력 회피 한계",
    theme: "gray",
    image:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuAgvPmg5JyUQ_IeCKCnM0rvKSLuOTdZcDtSt3gx7E0K2WGflbHKd-70vbPNrYRKq25Nn5h32nIpQIgAqgXxJ0TuxoKpkVtz4VLsW0YIA9QzphVnaqC6BnANDFTuDt74itcWD2jJpU5sVXRNRDqzqrF06-jgFDYPRHsrT1nTfU3wZGXWUJtOP3SJUyguAs-hbq71YaJKIZuiZbHKUA6yC_j5gyOPGbzXzAV_3HR8kFzdwcYhS_a2m4iTlA",
    overlay: "방어제동 가동",
    telemetry: "DECEL: -0.62G",
    legalTag: "신뢰의 원칙 및 불가항력 적용",
    explanation:
      "운전자 평균 인지 반응 시간(0.7초) 내에 급제동을 단행(-0.62G)했음에도 불구하고, 상대방의 급격한 침범으로 인해 충돌을 피할 수 없는 물리적 불가항력 상황이 증명되었습니다.",
    speedSelf: "41.5 km/h",
    speedOther: "53.1 km/h",
    distance: "3.4 m (임계)",
    yawRate: "1.8 deg/s",
    rangeVal: 108,
    scene: "차간거리 3.4m 급감 및 긴급 제동(-0.62G)",
    legal: "물리적 회피 불가항력 및 최선의 방어운전 입증",
    impact: "자차 측 추가 과실 가산 배제",
  },
  {
    id: "impact",
    step: "04",
    label: "충돌 시점",
    timestamp: "00:11.90",
    title: "우측 전면 범퍼-상대 좌측 후미 불가항력 접촉",
    short: "물리적 접촉 좌표 포착",
    status: "충돌 좌표 확정",
    theme: "dark",
    image:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuCgBQVFf7o5mp7tDLf8tSbWDsb1j9fFbkCObmowi5X8O8xojgnXPad3EI-_lBcSjNknLSUz15kWysm3B1kEGtxucuKSfM6nYAdfC9_ncTaGvqPH6jzdevhqSM2XvHmhCqDVF3JmHzxBiQS8eYPLG_4BOq2FwM2tKOhZifgJaZSDvs1yqj_8PdKadsBiY1PEpzuaqfcunThvwczaWcfpvkPW-GtrY3m-0UOMAhVIe6jWyDdAzv4Z9ItmWA",
    overlay: "물리적 충돌 포착",
    telemetry: "IMPACT FORCE 1.48G",
    legalTag: "손해보험협회 도표 252호 준용",
    explanation:
      "충돌 부위 및 각도 분석 결과, 직진 차선에서 주행하던 본인 차량의 조수석 앞범퍼를 대각선으로 끼어들던 상대 차량 후미가 덮치는 전형적인 차선변경 가해 사고로 확인되었습니다.",
    speedSelf: "32.1 km/h",
    speedOther: "49.8 km/h",
    distance: "0.0 m (접촉 발생)",
    yawRate: "67° 측면 각도",
    rangeVal: 119,
    scene: "우측 전면 범퍼와 상대 좌측 후미 접촉",
    legal: "차선 변경 사고의 충돌 위치 및 각도 분석",
    impact: "최종 예상 과실 20:80 판단 참고",
  },
];

const filters = [
  { id: "all", label: "전체 핵심 시점" },
  { id: "before5", label: "충돌 5초 전" },
  { id: "before3", label: "충돌 3초 전 (가감산 핵심)" },
  { id: "before1", label: "충돌 1초 전" },
  { id: "impact", label: "충돌 시점" },
];

function Time() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileAnalysisOpen, setMobileAnalysisOpen] = useState(true);
  const [filter, setFilter] = useState("all");
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [rangeValue, setRangeValue] = useState(0);
  const [playing, setPlaying] = useState(false);

  const filteredData =
    filter === "all"
      ? timelineData
      : timelineData.filter((item) => item.id === filter);

  const openVideo = (item) => {
    setSelectedVideo(item);
    setRangeValue(item.rangeVal);
    setPlaying(false);
  };

  const closeVideo = () => {
    setSelectedVideo(null);
    setPlaying(false);
  };

  const formatTime = (value) => {
    const seconds = value / 10;
    const whole = Math.floor(seconds);
    const fraction = Math.round((seconds - whole) * 100);
    return `00:${String(whole).padStart(2, "0")}.${String(
      fraction
    ).padStart(2, "0")}`;
  };

  return (
    <div className="time-page">
      {/* HEADER */}
      <header className="time-header">
        <div className="time-header-inner">
          <div className="time-header-left">
            <Link className="time-brand" to="/">
              <img
                className="time-brand-logo"
                src={avlyBrand}
                alt="에블리 캐릭터와 로고"
              />
              <span className="time-brand-text">
                <strong>Avly</strong>
                <span className="time-brand-korean">에블리</span>
                <span className="time-brand-divider">|</span>
                <span className="time-brand-description">AI 교통사고 과실 분석</span>
              </span>
            </Link>

            <nav className="time-navigation" aria-label="메인 메뉴">
              <Link className="time-nav-item" to="/home">홈</Link>
              <Link className="time-nav-item" to="/report">분석 결과</Link>
              <div className="time-nav-group">
                <button type="button" className="time-nav-item time-nav-active" aria-haspopup="true">
                  사고 분석
                </button>
                <div className="time-mega-menu" aria-label="사고 분석 메뉴">
                  <Link className="time-mega-menu-item time-mega-menu-current" to="/time" aria-current="page">
                    사고 순간 타임라인
                  </Link>
                  <Link className="time-mega-menu-item" to="/law">유사 판례 분석</Link>
                </div>
              </div>
              <Link className="time-nav-item" to="/home">사고 예방</Link>
            </nav>
          </div>

          <div className="time-header-right">
            <button
              type="button"
              className="time-mobile-menu-toggle"
              aria-label="메뉴 열기"
              aria-expanded={mobileMenuOpen}
              aria-controls="time-mobile-menu"
              onClick={() => setMobileMenuOpen((open) => !open)}
            >
              <span />
              <span />
              <span />
            </button>
          </div>
        </div>

      </header>

      {mobileMenuOpen && (
        <div className="time-mobile-menu-overlay" onClick={() => setMobileMenuOpen(false)}>
          <aside
            id="time-mobile-menu"
            className="time-mobile-menu-panel"
            aria-label="모바일 메뉴"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="time-mobile-menu-header">
              <Link to="/" className="time-mobile-menu-brand">
                <img
                  src={avlyMascot}
                  alt=""
                />
                <span><strong>Avly</strong> <small>교통사고 AI 분석</small></span>
              </Link>
              <button
                type="button"
                className="time-mobile-menu-close"
                aria-label="메뉴 닫기"
                onClick={() => setMobileMenuOpen(false)}
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <nav className="time-mobile-menu-list" aria-label="모바일 메뉴">
              <Link to="/home" className="time-mobile-menu-item" onClick={() => setMobileMenuOpen(false)}>
                <span className="material-symbols-outlined">home</span><span>홈</span>
              </Link>
              <Link to="/report" className="time-mobile-menu-item" onClick={() => setMobileMenuOpen(false)}>
                <span className="material-symbols-outlined">analytics</span><span>분석 결과</span>
              </Link>
              <div className="time-mobile-menu-analysis-row">
                <button type="button" className="time-mobile-menu-item time-mobile-menu-analysis time-mobile-menu-active" aria-expanded={mobileAnalysisOpen} aria-controls="time-mobile-analysis-submenu" onClick={() => setMobileAnalysisOpen((open) => !open)}>
                  <span className="material-symbols-outlined">error_outline</span><span>사고 분석</span><span className="material-symbols-outlined">expand_more</span>
                </button>
              </div>
              {mobileAnalysisOpen && (
                <div className="time-mobile-submenu" id="time-mobile-analysis-submenu">
                  <Link to="/time" aria-current="page" onClick={() => setMobileMenuOpen(false)}>
                    <span>사고 순간 타임라인</span><small className="time-mobile-menu-current">현재 화면</small>
                  </Link>
                  <Link to="/law" onClick={() => setMobileMenuOpen(false)}>
                    <span>유사 판례 분석</span><small>보기 &gt;</small>
                  </Link>
                </div>
              )}
              <Link to="/home" className="time-mobile-menu-item" onClick={() => setMobileMenuOpen(false)}>
                <span className="material-symbols-outlined">verified_user</span><span>사고 예방</span>
              </Link>
            </nav>
          </aside>
        </div>
      )}

      <main className="time-main">
        <div className="time-container">
          {/* BREADCRUMB */}
          <div className="time-breadcrumb">
            <span>사고 분석</span>
            <span className="material-symbols-outlined">
              chevron_right
            </span>
            <strong>사고 순간 타임라인</strong>
          </div>

          {/* SUMMARY */}
          <section className="time-summary">
            <div className="time-summary-heading">
              <h1>사고 순간 타임라인</h1>

              <div className="time-fault-chip">
                <div>
                  <span>내 최종 과실</span>
                  <strong className="my-fault">20<small>%</small></strong>
                </div>
                <b>:</b>
                <div>
                  <span>상대방 과실</span>
                  <strong className="other-fault">80<small>%</small></strong>
                </div>
              </div>
            </div>

            <div className="time-step-summary">
              <div className="time-step-summary-title">
                <span className="material-symbols-outlined">alt_route</span>
                4단계 핵심 판단 타임라인 요약
              </div>

              <div className="time-step-grid">
                {timelineData.map((item) => (
                  <div
                    key={item.id}
                    className={`time-step-item ${item.theme}`}
                  >
                    <div className="time-step-top">
                      <strong>STEP {item.step}</strong>
                      <span>{item.timestamp}</span>
                    </div>
                    <strong>{item.label}</strong>
                    <p>{item.short}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* FILTERS */}
          <div className="time-toolbar">
            <div className="time-filters">
              {filters.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`time-filter ${
                    filter === item.id ? "selected" : ""
                  }`}
                  onClick={() => setFilter(item.id)}
                >
                  {item.id !== "all" && (
                    <span className={`time-filter-dot ${item.id}`} />
                  )}
                  {item.label}
                  {item.id === "all" && <b>4</b>}
                </button>
              ))}
            </div>

            <button
              type="button"
              className="time-summary-button"
              onClick={() => setSummaryOpen(true)}
            >
              <span className="material-symbols-outlined">analytics</span>
              과실 산정 근거 요약
            </button>
          </div>

          {/* TIMELINE CARDS */}
          <div className="time-card-grid">
            {filteredData.map((item) => (
              <article
                key={item.id}
                className={`time-card ${item.theme}`}
              >
                <div className="time-card-content">
                  <div className="time-card-badges">
                    <span className="time-frame-badge">
                      {item.label} [{item.timestamp}]
                    </span>
                    <span className="time-status-badge">
                      {item.status}
                    </span>
                  </div>

                  <h2>{item.title}</h2>

                  <div className="time-snapshot">
                    <img src={item.image} alt={item.title} />
                    <div className="time-snapshot-overlay">
                      <span>
                        T: {item.timestamp} · {item.telemetry}
                      </span>
                      <strong>{item.overlay}</strong>
                    </div>
                  </div>
                </div>

                <div className="time-card-footer">
                  <button
                    type="button"
                    onClick={() => openVideo(item)}
                  >
                    <span className="material-symbols-outlined">
                      play_circle
                    </span>
                    영상보기
                  </button>
                </div>
              </article>
            ))}
          </div>
        </div>
      </main>

      {/* FOOTER */}
      <footer className="time-footer">
        <div className="time-footer-inner">
          <div className="time-legal-notice">
            <span className="material-symbols-outlined">
              verified_user
            </span>
            <div>
              <strong>법적 책임 고지 및 안내</strong>
              <p>
                본 서비스의 AI 영상 분석 결과와 예상 과실비율은
                참고자료이며, 실제 사고의 법적 책임이나 확정 판결을
                대신하지 않습니다.
              </p>
            </div>
            <button type="button">판례 기준 가이드라인</button>
          </div>

          <div className="time-footer-bottom">
            <div>
              <strong>Avly</strong> (에블리)
              <span> · 이용약관 · 개인정보처리방침 · 고객지원센터</span>
            </div>
            <p>© 2025 Avly Inc. All rights reserved.</p>
          </div>
        </div>
      </footer>

      {/* VIDEO MODAL */}
      {selectedVideo && (
        <div className="time-modal-overlay" onClick={closeVideo}>
          <div
            className="time-modal time-video-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="time-modal-header">
              <div className="time-modal-badges">
                <span className="time-modal-frame">
                  {selectedVideo.label} [{selectedVideo.timestamp}]
                </span>
                <span className="time-modal-status">
                  {selectedVideo.status}
                </span>
              </div>

              <button type="button" onClick={closeVideo}>
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="time-video-modal-body">
              <div className="time-player-column">
                <div
                  className="time-player"
                  style={{
                    backgroundImage: `linear-gradient(rgba(0,0,0,.12),rgba(0,0,0,.3)),url("${selectedVideo.image}")`,
                  }}
                >
                  <div className="time-player-top">
                    <span>REC ● 60.0 FPS</span>
                    <span>GPS: 37.5665° N, 126.9780° E</span>
                  </div>

                  <button
                    type="button"
                    className="time-play-button"
                    onClick={() => setPlaying(!playing)}
                    aria-label={playing ? "일시정지" : "재생"}
                  >
                    <span className="material-symbols-outlined">
                      {playing ? "pause" : "play_arrow"}
                    </span>
                  </button>

                  <div className="time-player-bottom">
                    <span>{formatTime(rangeValue)} SEC</span>
                    <span>AI OBJECT TRACKING: LOCKED</span>
                  </div>
                </div>

                <div className="time-scrubber">
                  <div>
                    <span>00:00.00</span>
                    <strong>{formatTime(rangeValue)}</strong>
                    <span>00:15.00</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="150"
                    value={rangeValue}
                    onChange={(e) =>
                      setRangeValue(Number(e.target.value))
                    }
                  />
                </div>
                <p className="time-demo-notice">
                  현재는 시연용 이미지 화면이며 실제 영상 재생은 연결되지
                  않았습니다.
                </p>
              </div>

              <div className="time-analysis-column">
                <h3>{selectedVideo.title}</h3>

                <div className="time-legal-tag">
                  <span className="material-symbols-outlined">balance</span>
                  {selectedVideo.legalTag}
                </div>

                <div className="time-explanation">
                  <strong>법률 및 인과관계 종합 판정</strong>
                  <p>{selectedVideo.explanation}</p>
                </div>

                <div className="time-telemetry">
                  <h4>차량 주행 데이터</h4>
                  <div><span>내 차량 속도</span><strong>{selectedVideo.speedSelf}</strong></div>
                  <div><span>상대 차량 속도</span><strong>{selectedVideo.speedOther}</strong></div>
                  <div><span>차간거리</span><strong>{selectedVideo.distance}</strong></div>
                  <div><span>차량 회전 데이터</span><strong>{selectedVideo.yawRate}</strong></div>
                </div>

                <button
                  type="button"
                  className="time-modal-close-button"
                  onClick={closeVideo}
                >
                  닫기
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUMMARY MODAL */}
      {summaryOpen && (
        <div
          className="time-modal-overlay"
          onClick={() => setSummaryOpen(false)}
        >
          <div
            className="time-modal time-summary-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="time-summary-modal-header">
              <div>
                <div className="time-analysis-label">
                  <span>ANALYSIS LOGIC</span>
                  Vision AI 초단위 추출 장면과 과실 산정 논리 요약
                </div>
                <h2>
                  영상의 어떤 장면이 어떤 판단 근거가 되었고,
                  <br />
                  그 결과 예상 과실 비율이 어떻게 산정되었는가?
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setSummaryOpen(false)}
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="time-summary-modal-body">
              {timelineData.slice(0, 3).map((item, index) => (
                <div
                  key={item.id}
                  className={`time-logic-card ${
                    index === 1 ? "decisive" : ""
                  }`}
                >
                  <div className="time-logic-heading">
                    <div>
                      <span className="time-logic-number">{index + 1}</span>
                      <strong>
                        장면 {index + 1} | {item.label} [{item.timestamp}]
                      </strong>
                    </div>
                    <span className="time-logic-status">{item.status}</span>
                  </div>

                  <div className="time-logic-columns">
                    <div>
                      <span>🎬 추출 장면</span>
                      <p>{item.scene}</p>
                    </div>
                    <div>
                      <span>⚖️ 법률 판단 근거</span>
                      <p>{item.legal}</p>
                    </div>
                    <div>
                      <span>📈 과실 산정 영향</span>
                      <p>{item.impact}</p>
                    </div>
                  </div>
                </div>
              ))}

              <div className="time-final-conclusion">
                <div>
                  <strong>⚖ 최종 결론 요약</strong>
                  <p>
                    기본 <b>30 : 70</b> → 깜빡이 미점등 및 급진입
                    수정요소 적용 (내 과실 -10%p 감산)
                  </p>
                </div>

                <div className="time-fault-chip">
                  <div>
                    <span>내 최종 과실</span>
                    <strong className="my-fault">20<small>%</small></strong>
                  </div>
                  <b>:</b>
                  <div>
                    <span>상대방 과실</span>
                    <strong className="other-fault">80<small>%</small></strong>
                  </div>
                </div>
              </div>
            </div>

            <div className="time-summary-modal-footer">
              <button
                type="button"
                onClick={() => setSummaryOpen(false)}
              >
                <span className="material-symbols-outlined">
                  check_circle
                </span>
                확인 완료
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Time;
