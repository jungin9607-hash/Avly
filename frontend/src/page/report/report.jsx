import { useState } from "react";
import Header from "../../components/layout/Header";
import Footer from "../../components/layout/Footer";
import { REPORT_SUMMARY, REASONS, TELEMETRY, EVIDENCES } from "../../data/report";
import { useToast } from "../../hooks/useToast";
import { ReasonItem, TelemetryItem, EvidenceItem } from "./ReportItems";
import "./report.css";

function Report() {
  const [shareOpen, setShareOpen] = useState(false);
  const [email, setEmail] = useState("");
  const { toast, showToast } = useToast();

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
      <Header />

      {/* MAIN */}
      <main className="report-main">
        <div className="report-container">
          {/* 분석 정보 상단 */}
          <section className="report-summary-header">
            <div className="summary-info">
              <div className="summary-code">
                <span>식별 코드</span>
                <strong>{REPORT_SUMMARY.code}</strong>
              </div>

              <div className="summary-divider" />

              <div className="summary-type">
                <span className="material-symbols-outlined">alt_route</span>
                <strong>사고 유형: {REPORT_SUMMARY.accidentType}</strong>
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
                    {REASONS.map((reason, index) => (
                      <ReasonItem key={reason.title} number={index + 1} {...reason} />
                    ))}
                  </div>
                </div>
              </section>

              {/* 속도 / TTC / 반응시간 */}
              <section className="telemetry-card">
                {TELEMETRY.map((item) => (
                  <TelemetryItem key={item.label} {...item} />
                ))}
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
                  {EVIDENCES.map((evidence) => (
                    <EvidenceItem key={evidence.title} {...evidence} />
                  ))}
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

      <Footer notice="본 서비스는 AI 영상 분석 엔진 및 대법원·손해보험협회 과실비율 인정기준 판례 데이터를 기반으로 제공되는 참고자료이며 법률적 대리 행위 또는 확정 판결을 대신하지 않습니다." />

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