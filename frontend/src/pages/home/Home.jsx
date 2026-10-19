import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import TopNav from "../../components/common/TopNav";
import ConsentModal from "../../components/home/ConsentModal";
import AnalysisProgressModal from "../../components/home/AnalysisProgressModal";
import SituationConfirmModal from "../../components/home/SituationConfirmModal";
import AdjustmentModal from "../../components/home/AdjustmentModal";
import NoticeModal from "../../components/home/NoticeModal";
import { ROUTES } from "../../routes";
import ReportPageLink from "./ReportPageLink";
import useAnalysisFlow from "./useAnalysisFlow";
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
    body: "에블리 AI 비전 모델은 영상 속 장면(이미지)만 분석하므로 블랙박스 내부 대화나 오디오 스트림은 전송 단계에서 완전 음소거 처리됩니다.",
  },
];

export default function Home() {
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState([]); // 동의 팝업을 기다리는 선택된 영상
  const [started, setStarted] = useState(false); // 동의하고 분석을 시작했는지
  const [params] = useSearchParams();
  const resumeId = params.get("resume"); // 결과 화면에서 "이어서 확인하기"로 들어온 분석 번호
  const { state: flow, start, choose, confirm, back, reset } = useAnalysisFlow(resumeId);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const unsupportedMessage = (name) => `${name}: MP4, MOV, AVI 영상만 올릴 수 있어요.`;

  // 영상은 하나만 받는다. 형식만 먼저 확인하고, 통과한 영상은 동의 팝업으로 넘김
  const selectFiles = (list) => {
    setError("");
    if (list.length > 1) {
      setError("영상은 한 번에 하나만 올릴 수 있어요.");
      return;
    }
    const file = list[0];
    if (!file) return;
    const ext = file.name.split(".").pop().toLowerCase();
    if (ACCEPT_EXT.includes(ext)) setPending([file]);
    else setError(unsupportedMessage(file.name));
  };

  // 팝업을 모두 닫고 처음 화면으로 돌아간다 (서버에서 진행 중인 분석은 계속된다)
  const closeAll = () => {
    reset();
    setPending([]);
    setStarted(false);
    if (resumeId) navigate(ROUTES.home, { replace: true });
  };

  const pickAnother = () => {
    closeAll();
    inputRef.current.click();
  };

  const begin = ({ retention }) => {
    setStarted(true);
    start(pending[0], retention);
  };

  // 결과가 나오면 결과 화면으로 이동한다
  useEffect(() => {
    if (flow.phase === "done") navigate(ROUTES.report(flow.analysisId));
  }, [flow.phase, flow.analysisId, navigate]);

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
              에블리는 손해보험협회 과실비율 인정기준과 판례 요약을 참고해 과실 비율을 안내하는 AI 참고 서비스예요.
              확정한 비율이 아니며 법적 효력이 없고, 최종 판단은 보험사 합의나 법원 판결에 따릅니다.
            </p>
          </footer>
        </div>
      </main>

      {/* 영상 선택 → 수집 동의 → 업로드·분석 → 사고 상황 확인 → 가감요소 질문 → 결과 */}
      {(pending.length > 0 || flow.phase !== "idle") && (
        <FlowModals
          file={pending[0]}
          started={started || flow.phase !== "idle"}
          flow={flow}
          onBegin={begin}
          onClose={closeAll}
          onPickAnother={pickAnother}
          onChoose={choose}
          onConfirm={confirm}
          onBack={back}
        />
      )}
    </div>
  );
}

/* ---------- 단계별 팝업 ---------- */
function FlowModals({ file, started, flow, onBegin, onClose, onPickAnother, onChoose, onConfirm, onBack }) {
  if (!started) return <ConsentModal fileName={file?.name} onStart={onBegin} onClose={onClose} onPickAnother={onPickAnother} />;
  switch (flow.phase) {
    case "uploading":
      return <AnalysisProgressModal phase="uploading" progress={flow.progress} onClose={onClose} />;
    case "analyzing":
      return <AnalysisProgressModal phase="analyzing" stage={flow.stage} onClose={onClose} />;
    case "finalizing":
    case "done":
      return <AnalysisProgressModal phase="finalizing" onClose={onClose} />;
    case "confirming":
      return <SituationConfirmModal situation={flow.situation} items={flow.catalog} onChoose={onChoose} onClose={onClose} />;
    case "adjusting":
      return <AdjustmentModal option={flow.option} questions={flow.questions} onSubmit={(answers) => onConfirm(flow.option, answers)} onBack={onBack} onClose={onClose} />;
    case "unsupported":
      return (
        <NoticeModal
          title="지원하지 않는 사고예요"
          desc={flow.unsupportedReason}
          primary={{ label: "다른 영상 선택", onClick: onPickAnother }}
          secondary={{ label: "닫기", onClick: onClose }}
        >
          <p className="md-hint">에블리는 지금 차량끼리 부딪힌 사고(차대차)만 분석할 수 있어요. 보행자, 이륜차, 자전거 사고는 보험사나 전문가에게 상담해 주세요.</p>
        </NoticeModal>
      );
    case "failed":
      return <FailedNotice error={flow.error} onPickAnother={onPickAnother} onClose={onClose} />;
    default:
      return <AnalysisProgressModal phase="uploading" progress={0} onClose={onClose} />;
  }
}

// 오류 코드별로 사용자에게 알려 줄 안내
const FAILURE = {
  VIDEO_TOO_LONG: { title: "영상이 너무 길어요", hint: "사고 전후 구간만 잘라서 다시 올려 주세요." }, // 서버 메시지에 길이 기준(최대 20초)이 들어 있다
  AI_NOT_CONFIGURED: { title: "분석 서비스를 준비하고 있어요", hint: "지금은 분석을 시작할 수 없어요. 잠시 후 다시 시도해 주세요." },
  NETWORK_ERROR: { title: "서버에 연결하지 못했어요", hint: "인터넷 연결을 확인하고 다시 시도해 주세요." },
  FILE_TOO_LARGE: { title: "영상 용량이 너무 커요", hint: "용량을 줄이거나 사고 전후 구간만 잘라서 올려 주세요." },
  UNSUPPORTED_FILE_TYPE: { title: "지원하지 않는 영상 형식이에요", hint: "MP4, MOV, AVI 영상만 올릴 수 있어요." },
};

function FailedNotice({ error, onPickAnother, onClose }) {
  const known = FAILURE[error?.code];
  return (
    <NoticeModal
      title={known?.title ?? "분석하지 못했어요"}
      desc={error?.message}
      primary={{ label: "다른 영상 선택", onClick: onPickAnother }}
      secondary={{ label: "닫기", onClick: onClose }}
    >
      {known && <p className="md-hint">{known.hint}</p>}
    </NoticeModal>
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
const IconShield = () => (
  <Svg size={18}>
    <path d="M12 3 5 6v5c0 4.5 3 8.5 7 10 4-1.5 7-5.5 7-10V6z" />
    <path d="m9.5 12 2 2 3.5-4" />
  </Svg>
);
