import { useState } from "react";
import Header from "../../components/layout/Header";
import Footer from "../../components/layout/Footer";
import { precedents, comparisonPoints, analysisImage } from "../../data/precedents";
import "./law.css";

function Law() {
  const [selectedId, setSelectedId] = useState(3);
  const [detailCase, setDetailCase] = useState(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const [notice, setNotice] = useState("");

  const selected =
    precedents.find((item) => item.id === selectedId) || precedents[0];

  const [myRatio, otherRatio] = selected.ratio.split(":").map(Number);

  return (
    <div className="law-page">
      <Header />

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
                    src={analysisImage}
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

      <Footer notice="본 서비스의 AI 분석 결과와 예상 과실비율 및 유사 판례 정보는 참고자료이며, 실제 법적 책임이나 확정 판결을 대신하지 않습니다." onGuidelineClick={() => setNotice("판례 기준 가이드라인은 추후 연결할 예정입니다.")} />

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
                  setNotice("PDF 다운로드 기능은 추후 연결할 예정입니다.")
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
