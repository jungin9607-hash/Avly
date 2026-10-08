
import { useState } from "react";
import { Link } from "react-router-dom";
import avlyBrand from "../../assets/avly-brand.png";
import avlyMascot from "../../assets/avly-mascot.png";
import "./law.css";

const precedents = [
  {
    id: 1,
    court: "서울중앙지방법원",
    caseNumber: "2022가단5188*** 판결",
    type: "손해배상(기) · 선고확정",
    similarity: "98.4%",
    ratio: "20:80",
    summary: "방향지시등 미작동 급차선 변경 후행 차량 추돌",
    icon: "emergency_share",
    detail:
      "상대 차량이 방향지시등 없이 2개 차로를 연속으로 급격히 변경 진입하였고, 직선 주행 중이던 청구인은 회피 가능 거리가 현저히 부족했던 사고입니다. 도로교통법 제19조 및 제38조 위반으로 피청구인 책임 80% 인정됨.",
    diff:
      "내 사고 대비 제동 개시 시점이 0.4초 빨라 과실 5%p 감경 요인 유효",
  },
  {
    id: 2,
    court: "수원지방법원",
    caseNumber: "2021나2043*** 판결",
    type: "구상금 · 항소기각 확정",
    similarity: "96.2%",
    ratio: "15:85",
    summary: "직진 차로 정상 주행 중 상대 차량 사선 급진입 및 급감속",
    icon: "merge_type",
    detail:
      "편도 3차로에서 1차로 직진 주행 중 우측 3차로에서 진입한 차량이 2차로를 통과해 1차로로 사선 급진입 후 급감속한 사안. 진입 차량의 후속 차량에 대한 통행방해 금지 의무 위반 중과실 인정.",
    diff:
      "상대 차량 속도 차이가 유사하나 본 사건은 주간, 판례는 야간 주행",
  },
  {
    id: 3,
    court: "대구지방법원",
    caseNumber: "2023나1109*** 판결",
    type: "손해배상(자) · 일부인용 확정",
    similarity: "94.7%",
    ratio: "10:90",
    summary: "백색 실선 차선변경 금지 위반 및 방향지시등 미점등",
    icon: "warning",
    detail:
      "교량 및 터널 진입 전 백색 실선 구간에서 방향지시등 없이 차선을 침범한 상대 차량의 사고. 피해 차량의 회피 불가능성이 시뮬레이션으로 입증됨.",
    diff:
      "사고 지점이 교차로 부근 점선 구간인지 실선 구간인지에 따른 법적 쟁점 차이 존재",
  },
];

const comparisonPoints = {
  common: [
    {
      title: "방향지시등 미점등 동일",
      content:
        "도로교통법 제38조(차의 신호) 위반 사실이 영상으로 명확히 판독됨.",
    },
    {
      title: "제한속도 준수",
      content:
        "내 차량 제한속도(60km/h 구간 54km/h 주행) 내 정상 직진 중 추돌.",
    },
    {
      title: "가해차량 급진입",
      content:
        "30미터 전방 안전거리 미확보 및 진로변경 금지 상황 연출.",
    },
  ],
  different: [
    {
      title: "충돌 부위",
      content:
        "판례는 전측면 추돌이었으나, 내 사고는 상대 차량 휠 하우스 사선 침범으로 회피 공간 전무.",
    },
    {
      title: "제동 반응 속도",
      content:
        "판례(0.9초) 대비 0.5초 빠른 감속 반응 확인으로 추가 5%p 유리 요인 도출.",
    },
    {
      title: "최종 예측 과실",
      content:
        "판례 기본 20:80보다 유리한 15:85 협상 권고.",
    },
  ],
};

function Law() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileAnalysisOpen, setMobileAnalysisOpen] = useState(true);
  const [selectedId, setSelectedId] = useState(3);
  const [detailCase, setDetailCase] = useState(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const [notice, setNotice] = useState("");

  const selected =
    precedents.find((item) => item.id === selectedId) || precedents[0];

  const [myRatio, otherRatio] = selected.ratio.split(":").map(Number);

  const showNotice = (message) => {
    setNotice(message);
  };

  return (
    <div className="law-page">
      {/* 상단 헤더 */}
      <header className="law-header">
        <div className="law-header-inner">
          <div className="law-header-left">
            <Link className="law-brand" to="/">
              <img
                src={avlyBrand}
                alt="에블리 캐릭터와 로고"
              />
              <span className="law-brand-text">
                <strong>Avly</strong>
                <span className="law-brand-korean">에블리</span>
                <span className="law-brand-divider">|</span>
                <span className="law-brand-description">AI 교통사고 과실 분석</span>
              </span>
            </Link>

            <nav className="law-nav" aria-label="메인 메뉴">
              <Link className="law-nav-item" to="/home">홈</Link>
              <Link className="law-nav-item" to="/report">분석 결과</Link>
              <div className="law-nav-group">
                <button type="button" className="law-nav-item law-nav-active" aria-haspopup="true">사고 분석</button>
                <div className="law-mega-menu" aria-label="사고 분석 메뉴">
                  <Link className="law-mega-menu-item" to="/time">사고 순간 타임라인</Link>
                  <Link className="law-mega-menu-item law-mega-menu-current" to="/law" aria-current="page">유사 판례 분석</Link>
                </div>
              </div>
              <Link className="law-nav-item" to="/home">사고 예방</Link>
            </nav>
          </div>

          <div className="law-header-right">
            <button
              type="button"
              className="law-mobile-menu-toggle"
              aria-label="메뉴 열기"
              aria-expanded={mobileMenuOpen}
              aria-controls="law-mobile-menu"
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
        <div className="law-mobile-menu-overlay" onClick={() => setMobileMenuOpen(false)}>
          <aside
            id="law-mobile-menu"
            className="law-mobile-menu-panel"
            aria-label="모바일 메뉴"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="law-mobile-menu-header">
              <Link to="/" className="law-mobile-menu-brand">
                <img
                  src={avlyMascot}
                  alt=""
                />
                <span><strong>Avly</strong> <small>교통사고 AI 분석</small></span>
              </Link>
              <button
                type="button"
                className="law-mobile-menu-close"
                aria-label="메뉴 닫기"
                onClick={() => setMobileMenuOpen(false)}
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <nav className="law-mobile-menu-list" aria-label="모바일 메뉴">
              <Link to="/home" className="law-mobile-menu-item" onClick={() => setMobileMenuOpen(false)}>
                <span className="material-symbols-outlined">home</span><span>홈</span>
              </Link>
              <Link to="/report" className="law-mobile-menu-item" onClick={() => setMobileMenuOpen(false)}>
                <span className="material-symbols-outlined">analytics</span><span>분석 결과</span>
              </Link>
              <div className="law-mobile-menu-analysis-row">
                <button type="button" className="law-mobile-menu-item law-mobile-menu-analysis law-mobile-menu-active" aria-expanded={mobileAnalysisOpen} aria-controls="law-mobile-analysis-submenu" onClick={() => setMobileAnalysisOpen((open) => !open)}>
                  <span className="material-symbols-outlined">error_outline</span><span>사고 분석</span><span className="material-symbols-outlined">expand_more</span>
                </button>
              </div>
              {mobileAnalysisOpen && (
                <div className="law-mobile-submenu" id="law-mobile-analysis-submenu">
                  <Link to="/time" onClick={() => setMobileMenuOpen(false)}>
                    <span>사고 순간 타임라인</span><small>보기 &gt;</small>
                  </Link>
                  <Link to="/law" aria-current="page" onClick={() => setMobileMenuOpen(false)}>
                    <span>유사 판례 분석</span><small className="law-mobile-menu-current">현재 화면</small>
                  </Link>
                </div>
              )}
              <Link to="/home" className="law-mobile-menu-item" onClick={() => setMobileMenuOpen(false)}>
                <span className="material-symbols-outlined">verified_user</span><span>사고 예방</span>
              </Link>
            </nav>
          </aside>
        </div>
      )}

      <main className="law-main">
        <div className="law-container">
          <div className="law-breadcrumb" aria-label="현재 위치">
            <span>사고 분석</span>
            <span className="material-symbols-outlined" aria-hidden="true">
              chevron_right
            </span>
            <strong>유사 판례 분석</strong>
          </div>

          {/* 제목 */}
          <div className="law-heading">
            <div>
              <h1>유사 판례 분석</h1>
            </div>

            <div className="law-heading-badge">
              <span className="law-dot" />
              가장 유사한 3대 판례
            </div>
          </div>

          {/* 판례 목록 및 AI 분석 */}
          <div className="law-content-grid">
            <section className="law-precedent-list">
              {precedents.map((item, index) => {
                const isSelected = selectedId === item.id;

                return (
                  <article
                    key={item.id}
                    className={`law-precedent-card ${
                      isSelected ? "selected" : ""
                    }`}
                    onClick={() => setSelectedId(item.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setSelectedId(item.id);
                      }
                    }}
                  >
                    <div className="law-card-top">
                      <div className="law-case-identity">
                        <span
                          className={`law-radio ${
                            isSelected ? "checked" : ""
                          }`}
                        >
                          <span className="material-symbols-outlined">
                            check
                          </span>
                        </span>

                        <span
                          className={`law-case-rank ${
                            index === 0 ? "first" : ""
                          }`}
                        >
                          {index + 1}
                        </span>

                        <div className="law-case-title">
                          <div className="law-court-line">
                            <strong>{item.court}</strong>
                            <span>{item.caseNumber}</span>
                          </div>
                          <p>{item.type}</p>
                        </div>
                      </div>

                      <span
                        className={`law-similarity ${
                          index === 0 ? "highest" : ""
                        }`}
                      >
                        <span className="material-symbols-outlined">
                          verified
                        </span>
                        유사도 {item.similarity}
                      </span>
                    </div>

                    <div className="law-accident-summary">
                      <span className="material-symbols-outlined">
                        {item.icon}
                      </span>
                      <span>사고 상황: {item.summary}</span>
                    </div>

                    <div className="law-card-bottom">
                      <div className="law-selection-status">
                        <span
                          className={`law-status-dot ${
                            isSelected ? "active" : ""
                          }`}
                        />
                        <strong className={isSelected ? "active" : ""}>
                          {isSelected ? "현재 선택됨" : "선택 가능"}
                        </strong>
                        <span>기준 과실 {item.ratio.replace(":", " : ")}</span>
                      </div>

                      <button
                        type="button"
                        className="law-detail-button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setDetailCase(item);
                        }}
                      >
                        상세보기
                        <span className="material-symbols-outlined">
                          open_in_new
                        </span>
                      </button>
                    </div>
                  </article>
                );
              })}
            </section>

            {/* 오른쪽 AI 매칭 요약 */}
            <aside className="law-sidebar">
              <div className="law-ai-card">
                <div className="law-ai-title">
                  <strong>
                    <span className="material-symbols-outlined">
                      smart_toy
                    </span>
                    AI 판례 유사도 매칭 요약
                  </strong>
                  <span className="law-confidence">신뢰도 98%</span>
                </div>

                <div className="law-ratio-panel">
                  <div className="law-ratio-label">
                    <span>선택된 판례 과실</span>
                    <strong>{selected.ratio}</strong>
                  </div>

                  <div className="law-ratio-bar">
                    <div
                      className="law-ratio-my"
                      style={{ width: `${myRatio}%` }}
                    />
                    <div
                      className="law-ratio-other"
                      style={{ width: `${otherRatio}%` }}
                    />
                  </div>

                  <div className="law-ratio-caption">
                    <span>내 과실 {myRatio}%</span>
                    <span>상대 차량 {otherRatio}%</span>
                  </div>
                </div>

                <div className="law-ai-insights">
                  <p>
                    <span className="material-symbols-outlined">
                      check_circle
                    </span>
                    <span>
                      <strong>동일 차선 급진입</strong> 형태의 사고로서
                      서울중앙지법 및 수원지법 판결 기준이 가장 높게
                      적용됩니다.
                    </span>
                  </p>

                  <p>
                    <span className="material-symbols-outlined">
                      check_circle
                    </span>
                    <span>
                      내 차량의 브레이크 작동 텔레메트리 데이터가
                      판례 상 <strong>불가항력 방어운전</strong> 법리에
                      부합합니다.
                    </span>
                  </p>
                </div>

                <div className="law-analysis-image">
                  <img
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuBcVQu-7YcxxzzlZVb0f_dnGe_NxDfUw_vbHLmeHaZj7926hRCT5AAeMSwTXQeAXKWwnTWzVvrjSi2lqnZxnD7Ljyfx4ts8ktbNZwSvnry2xc_a1ZTPneheAmafhCF81q35knOMNXERY_lYM_Ryt9nRwPM7dJ0Ve7fRdfTIASVmXdfnvmJt8vWGxYoV2z59E8bvMWbXVAKjOywBbTEDKkSIHxYGOghF7MONvvVqoIMHHFaK_4_j4BC_0A"
                    alt="교통사고 차량 궤적 분석"
                  />
                  <div className="law-analysis-image-caption">
                    <span className="material-symbols-outlined">
                      videocam
                    </span>
                    블랙박스 궤적 분석 연동 완료
                  </div>
                </div>
              </div>

              <div className="law-guide-card">
                <h3>
                  <span className="material-symbols-outlined">info</span>
                  판례 활용 가이드
                </h3>
                <p>
                  보험사와 과실비율을 협의할 때 유사 사고의 판단
                  근거를 참고자료로 활용할 수 있습니다. 실제 판결
                  내용과 사건번호는 반드시 확인해야 합니다.
                </p>
              </div>
            </aside>
          </div>

          {/* 하단 비교 버튼 */}
          <section className="law-compare-section">
            <h2>선택한 판례와 내 사고 비교하기</h2>

            <button
              type="button"
              className="law-compare-button"
              onClick={() => setCompareOpen(true)}
            >
              <span className="material-symbols-outlined">
                compare_arrows
              </span>
              선택한 판례와 내 사고 비교하기
            </button>

            <p>
              현재 선택 기준:{" "}
              <strong>
                {selected.court} {selected.caseNumber}
              </strong>
            </p>
          </section>
        </div>
      </main>

      {/* 하단 안내 */}
      <footer className="law-footer">
        <div className="law-footer-inner">
          <div className="law-legal-notice">
            <span className="material-symbols-outlined">
              verified_user
            </span>
            <div>
              <strong>법적 책임 고지 및 안내</strong>
              <p>
                본 서비스의 AI 분석 결과와 예상 과실비율 및 유사 판례
                정보는 참고자료이며, 실제 법적 책임이나 확정 판결을
                대신하지 않습니다.
              </p>
            </div>
            <button type="button" onClick={() => showNotice("판례 기준 가이드라인은 추후 연결할 예정입니다.")}>
              판례 기준 가이드라인
            </button>
          </div>

          <div className="law-footer-bottom">
            <div>
              <strong>Avly</strong> (에블리)
              <span> · 이용약관 · 개인정보처리방침 · 고객지원센터</span>
            </div>
            <p>© 2025 Avly Inc. All rights reserved.</p>
          </div>
        </div>
      </footer>

      {/* 판례 상세보기 팝업 */}
      {detailCase && (
        <div
          className="law-modal-overlay"
          onClick={() => setDetailCase(null)}
        >
          <div
            className="law-modal law-detail-modal"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="law-modal-heading">
              <div>
                <span className="law-modal-eyebrow">
                  <span className="material-symbols-outlined">gavel</span>
                  판례 원문 및 해설
                </span>
                <h2>{detailCase.court} 판결</h2>
                <p>{detailCase.caseNumber}</p>
              </div>

              <button
                type="button"
                className="law-close-button"
                onClick={() => setDetailCase(null)}
                aria-label="닫기"
              >
                <span className="material-symbols-outlined">
                  close
                </span>
              </button>
            </div>

            <div className="law-detail-ratio">
              <div>
                <span>판결 인정 과실 비율</span>
                <strong>{detailCase.ratio}</strong>
              </div>
              <span>유사도 {detailCase.similarity}</span>
            </div>

            <div className="law-modal-section">
              <h3>사건 개요 및 사고 상황</h3>
              <p className="law-modal-highlight">{detailCase.summary}</p>
            </div>

            <div className="law-modal-section">
              <h3>재판부 판결 요지 및 법적 근거</h3>
              <p className="law-modal-light">{detailCase.detail}</p>
            </div>

            <div className="law-modal-section">
              <h3>내 사고와의 정밀 분석 쟁점</h3>
              <p className="law-modal-blue">{detailCase.diff}</p>
            </div>

            <div className="law-modal-actions">
              <button
                type="button"
                className="law-primary-button"
                onClick={() => setDetailCase(null)}
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 내 사고 비교 팝업 */}
      {compareOpen && (
        <div
          className="law-modal-overlay"
          onClick={() => setCompareOpen(false)}
        >
          <div
            className="law-modal law-compare-modal"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="law-modal-heading">
              <div>
                <h2>내 사고 vs {selected.court} 판례 정밀 대조</h2>
              </div>

              <button
                type="button"
                className="law-close-button"
                onClick={() => setCompareOpen(false)}
                aria-label="닫기"
              >
                <span className="material-symbols-outlined">
                  close
                </span>
              </button>
            </div>

            <div className="law-comparison-grid">
              <div className="law-comparison-column common">
                <h3>
                  <span className="material-symbols-outlined">
                    check_circle
                  </span>
                  공통점
                </h3>

                {comparisonPoints.common.map((point) => (
                  <div key={point.title} className="law-comparison-item">
                    <strong>{point.title}:</strong> {point.content}
                  </div>
                ))}
              </div>

              <div className="law-comparison-column different">
                <h3>
                  <span className="material-symbols-outlined">
                    auto_graph
                  </span>
                  차이점
                </h3>

                {comparisonPoints.different.map((point) => (
                  <div key={point.title} className="law-comparison-item">
                    <strong>{point.title}:</strong> {point.content}
                  </div>
                ))}
              </div>
            </div>

            <div className="law-download-panel">
              <div>
                <span className="material-symbols-outlined">
                  description
                </span>
                <div>
                  <strong>정밀 대조 분석 의견서 다운로드</strong>
                  <p>보험사 제출용 PDF 리포트 (판례 첨부 포함)</p>
                </div>
              </div>

              <button
                type="button"
                className="law-primary-button"
                onClick={() =>
                  showNotice("PDF 다운로드 기능은 추후 연결할 예정입니다.")
                }
              >
                <span className="material-symbols-outlined">
                  download
                </span>
                PDF 다운로드
              </button>
            </div>

            <div className="law-modal-actions">
              <button
                type="button"
                className="law-secondary-button"
                onClick={() => setCompareOpen(false)}
              >
                확인
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 안내 팝업 */}
      {notice && (
        <div
          className="law-notice-overlay"
          onClick={() => setNotice("")}
        >
          <div
            className="law-notice"
            onClick={(e) => e.stopPropagation()}
          >
            <p>{notice}</p>
            <button
              type="button"
              onClick={() => setNotice("")}
            >
              확인
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Law;
