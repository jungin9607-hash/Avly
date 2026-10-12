import { useState } from "react";
import Header from "../../components/layout/Header";
import Footer from "../../components/layout/Footer";
import { timelineData, filters } from "../../data/timeline";
import "./time.css";

const formatTime = (value) => {
  const seconds = value / 10;
  const whole = Math.floor(seconds);
  const fraction = Math.round((seconds - whole) * 100);
  return `00:${String(whole).padStart(2, "0")}.${String(fraction).padStart(2, "0")}`;
};

function Time() {
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

  return (
    <div className="time-page">
      <Header />

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

      <Footer notice="본 서비스의 AI 영상 분석 결과와 예상 과실비율은 참고자료이며, 실제 사고의 법적 책임이나 확정 판결을 대신하지 않습니다." onGuidelineClick={() => {}} />

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
