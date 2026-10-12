import { useNavigate } from "react-router-dom";
import avlyCharacterWordmark from "../../assets/avly-character-wordmark-transparent.png";
import Header from "../../components/layout/Header";
import Footer from "../../components/layout/Footer";
import "./intro.css";

function Intro() {
  const navigate = useNavigate();

  return (
    <div className="home-page">
      <Header />

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

      <Footer notice="본 서비스는 AI 영상 분석 엔진 및 대법원·손해보험협회 과실비율 인정기준 판례 데이터를 기반으로 제공되는 객관적 참고자료이며, 변호사법 제109조에 따른 법률적 대리 행위 또는 확정 판결을 대신하지 않습니다." onGuidelineClick={() => {}} />
    </div>
  );
}

export default Intro;