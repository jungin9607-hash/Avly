import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import TopNav from "../../components/common/TopNav";
import ConsentModal from "../../components/home/ConsentModal";
import QuestionModal from "../../components/home/QuestionModal";
import AnalysisProgressModal from "../../components/home/AnalysisProgressModal";
import SituationConfirmModal from "../../components/home/SituationConfirmModal";
import ReportPageLink from "./ReportPageLink";
import "./Home.css";

const ACCEPT_EXT = ["mp4", "mov", "avi"];
const MAX_MB = 50;

const GUIDES = [
  {
    title: "전방 블랙박스 영상 권장",
    body: "상대 차량의 진입 각도, 도로 차선(실선·점선), 노면 표시 및 신호등 점등 상태가 뚜렷하게 식별될수록 분석 오차가 대폭 감소합니다.",
  },
  {
    title: "사고 전후 15초 내외 구간",
    body: "충돌 시점 기준 최소 10초 전 진입 단계부터 충돌 직후 5초 정지 화면까지 포함되어야 AI가 예측 가능성 및 제동 회피 여부를 정확히 판별합니다.",
  },
  {
    title: "음성 녹음 여부 무관",
    body: "에블리 AI 비전 모델은 순수 시각 좌표 및 텔레메트리 궤적만을 추출하므로 블랙박스 내부 대화나 오디오 스트림은 전송 단계에서 완전 음소거 처리됩니다.",
  },
];

const DEMO_FILE_NAME = "블랙박스_시연용_차선사고.mp4";

export default function Home() {
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState([]); // 동의 팝업을 기다리는 선택된 영상
  const [demoConsent, setDemoConsent] = useState(false); // 시연 파일로 동의 팝업을 연 경우
  const [popupStep, setPopupStep] = useState("consent");
  const [answers, setAnswers] = useState({});

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const unsupportedMessage = (name) => `${name}: MP4, MOV, AVI 영상만 올릴 수 있어요.`;

  // 형식만 먼저 확인하고, 통과한 영상은 동의 팝업으로 넘김
  const selectFiles = (list) => {
    setError("");
    const valid = [];
    for (const file of list) {
      const ext = file.name.split(".").pop().toLowerCase();
      if (ACCEPT_EXT.includes(ext)) valid.push(file);
      else setError(unsupportedMessage(file.name));
    }
    if (valid.length) setPending(valid);
  };

  // 답변은 홈에서 보관해 질문 사이를 이동해도 선택값을 유지한다.
  const updateAnswer = (key, value) => {
    setAnswers((current) => ({ ...current, [key]: value }));
  };

  const finishAnalysis = () => {
    closeConsent();
    navigate("/analysis-test");
  };

  const closeConsent = () => {
    setPending([]);
    setDemoConsent(false);
    setPopupStep("consent");
    setAnswers({});
  };

  const pickAnother = () => {
    closeConsent();
    inputRef.current.click();
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    selectFiles(e.dataTransfer.files);
  };

  const onDragLeave = (e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) setDragging(false);
  };

  return (
    <div className="uh">
      <TopNav active="홈" theme="dark" />

      {/* 주요 부분: 네이비 배경과 옅은 브랜드 글자 위에 업로드와 가이드 */}
      <section className="uh-hero">
        <div className="uh-grid">
          {/* 왼쪽: 글(단계 · 제목 · 형식 안내)과 그 아래 작은 업로드 상자 */}
          <div className="uh-intro">
            <ol className="uh-steps" aria-label="분석 단계">
              <li className="on">영상 업로드</li>
              <li>AI 분석</li>
              <li>결과 확인</li>
            </ol>
            <h1>블랙박스 영상 분석</h1>
            <p className="uh-lead">
              MP4, MOV, AVI 포맷 지원 · 단일 파일 최대 <strong>{MAX_MB}MB</strong> 이내 권장
            </p>

            <section
              className={dragging ? "uh-drop is-over" : "uh-drop"}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
            >
              <div className="uh-drop-icon">
                <IconUpload />
              </div>
              <h2>블랙박스 동영상 파일을 이곳에 끌어다 놓으세요</h2>
              <button type="button" className="uh-btn uh-btn-solid" onClick={() => inputRef.current.click()}>
                <IconPlus />
                블랙박스 영상 업로드
              </button>
              <input
                ref={inputRef}
                type="file"
                accept=".mp4,.mov,.avi,video/mp4,video/quicktime,video/x-msvideo"
                multiple
                hidden
                onChange={(e) => {
                  selectFiles(e.target.files);
                  e.target.value = "";
                }}
              />
              {error && (
                <p className="uh-error" role="alert">
                  {error}
                </p>
              )}
            </section>
            <button
              type="button"
              className="uh-btn uh-btn-line uh-demo-trigger"
              onClick={() => setDemoConsent(true)}
            >
              <IconBolt />
              단계별 분석 팝업 시연
            </button>
          </div>

          {/* 오른쪽: 영상 가이드 타일 3개 */}
          <aside className="uh-guides">
            <h2 className="uh-guides-title">정확한 분석을 위한 영상 가이드</h2>
            {/* 타일 아래쪽 꼭지가 다음 타일을 가리켜 하나의 흐름으로 이어짐 */}
            <ol className="uh-tiles">
              {GUIDES.map((g, i) => (
                <li key={g.title} className={`uh-tile uh-tile-${i + 1}`}>
                  <p className="uh-tag">
                    STEP <b>{String(i + 1).padStart(2, "0")}</b>
                  </p>
                  <h3>{g.title}</h3>
                  <p className="uh-tile-body">{g.body}</p>
                </li>
              ))}
            </ol>
          </aside>
        </div>
      </section>

      <main className="uh-main">
        <div className="uh-footer">
          <ReportPageLink />
          <footer className="uh-notice">
            <IconShield />
            <p>
              에블리는 대한민국 손해보험협회 과실비율 분쟁심의위원회 기본 인정기준과 법원 확정 판결 데이터셋에 기초하여
              확률적 과실 분포를 제공합니다. 최종 법적 효력은 보험사 합의 또는 법원 판결에 따릅니다.
            </p>
          </footer>
        </div>
      </main>

      {/* 영상 선택 → 수집 동의 → 질문 1 → 질문 2 → 분석 중 → 사고 상황 확인 */}
      {(pending.length > 0 || demoConsent) &&
        (popupStep === "consent" ? (
          <ConsentModal
            fileNames={demoConsent ? [DEMO_FILE_NAME] : pending.map((f) => f.name)}
            onStart={() => setPopupStep("questions-1")}
            onClose={closeConsent}
            onPickAnother={pickAnother}
          />
        ) : popupStep === "questions-1" ? (
          <QuestionModal
            key="questions-1"
            stage={0}
            answers={answers}
            onAnswerChange={updateAnswer}
            onSubmit={() => setPopupStep("questions-2")}
            onClose={closeConsent}
          />
        ) : popupStep === "questions-2" ? (
          <QuestionModal
            key="questions-2"
            stage={1}
            answers={answers}
            onAnswerChange={updateAnswer}
            onSubmit={() => setPopupStep("analyzing")}
            onBack={() => setPopupStep("questions-1")}
            onClose={closeConsent}
          />
        ) : popupStep === "analyzing" ? (
          <AnalysisProgressModal
            step={4}
            description="사고 장면과 차량 움직임을 분석하고 있어요."
            onComplete={() => setPopupStep("confirm")}
            onClose={closeConsent}
          />
        ) : (
          <SituationConfirmModal
            onConfirm={finishAnalysis}
            onBack={() => setPopupStep("questions-1")}
            onClose={closeConsent}
          />
        ))}
    </div>
  );
}

/* ---------- 아이콘 (선 아이콘, currentColor) ---------- */
const Svg = ({ children, size = 20 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);
const IconUpload = () => (
  <Svg size={30}>
    <path d="M7 18a4.5 4.5 0 0 1-.6-8.96A6 6 0 0 1 18 8.5a4 4 0 0 1-.5 9.5" />
    <path d="M12 12v8M8.5 15.5 12 12l3.5 3.5" />
  </Svg>
);
const IconPlus = () => (
  <Svg size={18}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 8v8M8 12h8" />
  </Svg>
);
const IconBolt = () => (
  <Svg size={16}>
    <path d="M13 2 4 14h7l-1 8 9-12h-7z" />
  </Svg>
);
const IconShield = () => (
  <Svg size={18}>
    <path d="M12 3 5 6v5c0 4.5 3 8.5 7 10 4-1.5 7-5.5 7-10V6z" />
    <path d="m9.5 12 2 2 3.5-4" />
  </Svg>
);
