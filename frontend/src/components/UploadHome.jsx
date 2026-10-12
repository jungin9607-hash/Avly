import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import TopNav from "./TopNav";
import ConsentModal from "./ConsentModal";
import QuestionModal from "./QuestionModal";
import purpleWeave from "../assets/purple-weave.jpg";
import "./UploadHome.css";

const ACCEPT_EXT = ["mp4", "mov", "avi"];
const MAX_MB = 500;

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

const DEMO_FILE = {
  id: "demo",
  name: "블랙박스_시연용_차선사고.mp4",
  size: 38.5 * 1024 * 1024,
  duration: 24,
  quality: "FHD 60fps",
  status: "ready",
  demo: true,
};

const formatSize = (bytes) => `${(bytes / 1024 / 1024).toFixed(1)} MB`;
const formatTime = (sec) => {
  const s = Math.round(sec);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
};
const qualityOf = (h) => (h >= 2160 ? "4K" : h >= 1440 ? "QHD" : h >= 1080 ? "FHD" : h >= 720 ? "HD" : `${h}p`);

// 브라우저에서 영상 길이·해상도만 읽어 옴 (업로드 전)
function readVideoMeta(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const video = document.createElement("video");
    video.preload = "metadata";
    const done = (meta) => {
      URL.revokeObjectURL(url);
      resolve(meta);
    };
    video.onloadedmetadata = () =>
      done({
        duration: Number.isFinite(video.duration) ? video.duration : null,
        quality: video.videoHeight ? qualityOf(video.videoHeight) : null,
      });
    video.onerror = () => done({ duration: null, quality: null });
    video.src = url;
  });
}

export default function UploadHome() {
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const [files, setFiles] = useState([DEMO_FILE]);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState([]); // 동의 팝업을 기다리는 선택된 영상
  const [demoConsent, setDemoConsent] = useState(false); // 시연 파일로 동의 팝업을 연 경우
  const [consent, setConsent] = useState(null); // 동의 단계를 마치면 채워지고, 그때 질문 팝업이 열림

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

  // 2단계 질문 팝업에서 "답변 제출하고…" → 목록에 등록 (동의 여부와 관계없이 진행)
  const submitAnswers = (answers) => {
    const survey = { consent, answers };
    if (demoConsent) {
      setFiles((prev) => prev.map((f) => (f.demo ? { ...f, ...survey } : f)));
      closeConsent();
      // TODO: 실제 분석 결과(동의·답변 반영)를 넘겨주기. 지금은 시연용 결과 화면으로 이동
      navigate("/analysis-test");
      return;
    }
    for (const file of pending) {
      const id = `${file.name}-${file.size}-${file.lastModified}`;
      const entry = {
        id,
        name: file.name,
        size: file.size,
        status: "reading",
        tooLarge: file.size > MAX_MB * 1024 * 1024,
        ...survey,
      };
      setFiles((prev) => (prev.some((f) => f.id === id) ? prev : [...prev, entry]));
      readVideoMeta(file).then((meta) =>
        setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, ...meta, status: "ready" } : f)))
      );
    }
    closeConsent();
    // TODO: 실제 분석 결과(동의·답변 반영)를 넘겨주기. 지금은 시연용 결과 화면으로 이동
    navigate("/analysis-test");
  };

  const closeConsent = () => {
    setPending([]);
    setDemoConsent(false);
    setConsent(null);
  };

  const simulateUnsupported = () => {
    closeConsent();
    setError(unsupportedMessage("시연용_지원하지_않는_파일.wmv"));
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

  const removeFile = (id) => setFiles((prev) => prev.filter((f) => f.id !== id));
  const readyCount = files.filter((f) => f.status === "ready").length;

  return (
    <div className="uh">
      <TopNav active="홈" theme="dark" />

      {/* 주요 부분: #8C4D8C 직조 질감 사진 배경 위에 업로드와 가이드 */}
      <section className="uh-hero" style={{ "--hero-photo": `url(${purpleWeave})` }}>
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
                    <span className="uh-tag-of"> / {String(GUIDES.length).padStart(2, "0")}</span>
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
        {/* 파일 목록 */}
        <section className="uh-list">
          <div className="uh-list-head">
            <h3>
              <IconFilm />
              등록된 시연 파일 목록
            </h3>
            <span className="uh-count">{readyCount}개 준비됨</span>
          </div>

          {files.length === 0 ? (
            <p className="uh-empty">아직 등록된 영상이 없어요.</p>
          ) : (
            <ul className="uh-files">
              {files.map((f) => (
                <li key={f.id} className="uh-file">
                  <div className="uh-file-icon">
                    <IconVideo />
                  </div>
                  <div className="uh-file-info">
                    <p className="uh-file-name">
                      <span>{f.name}</span>
                      {f.quality && <em>{f.quality}</em>}
                    </p>
                    <p className="uh-file-meta">
                      {formatSize(f.size)}
                      <i />
                      재생시간 {f.duration != null ? formatTime(f.duration) : "--:--"}
                      <i />
                      {f.status === "ready" ? (
                        <span className="uh-ready">
                          <IconCheck />
                          준비 완료
                        </span>
                      ) : (
                        <span className="uh-reading">확인 중…</span>
                      )}
                    </p>
                    {f.tooLarge && <p className="uh-warn">권장 용량(500MB)보다 커서 분석이 오래 걸릴 수 있어요.</p>}
                  </div>
                  <div className="uh-file-actions">
                    {/* 시연 파일은 동의 팝업부터 띄움. 일반 파일 버튼은 TODO: 분석 단계와 연결 */}
                    <button
                      type="button"
                      className="uh-btn uh-btn-line"
                      disabled={f.status !== "ready"}
                      onClick={f.demo ? () => setDemoConsent(true) : undefined}
                    >
                      <IconBolt />
                      {f.demo ? "단계별 분석 팝업 시연" : "AI 분석 시작"}
                    </button>
                    {!f.demo && (
                      <button type="button" className="uh-remove" aria-label={`${f.name} 삭제`} onClick={() => removeFile(f.id)}>
                        ×
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <footer className="uh-notice">
          <IconShield />
          <p>
            에블리는 대한민국 손해보험협회 과실비율 분쟁심의위원회 기본 인정기준과 법원 확정 판결 데이터셋에 기초하여
            확률적 과실 분포를 제공합니다. 최종 법적 효력은 보험사 합의 또는 법원 판결에 따릅니다.
          </p>
        </footer>
      </main>

      {/* 영상 선택 → 1단계 수집 동의 → 2단계 확인 질문 */}
      {(pending.length > 0 || demoConsent) &&
        (consent ? (
          <QuestionModal onSubmit={submitAnswers} onClose={closeConsent} />
        ) : (
          <ConsentModal
            fileNames={demoConsent ? [DEMO_FILE.name] : pending.map((f) => f.name)}
            onStart={setConsent}
            onClose={closeConsent}
            onSimulateUnsupported={simulateUnsupported}
            onPickAnother={pickAnother}
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
const IconFilm = () => (
  <Svg size={18}>
    <rect x="3" y="7" width="18" height="13" rx="2" />
    <path d="m3 7 3-4 3 4M9 7l3-4 3 4M15 7l3-4 3 4" />
  </Svg>
);
const IconVideo = () => (
  <Svg>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
    <path d="M14 3v5h5" />
    <path d="m10 11 4 2.5-4 2.5z" />
  </Svg>
);
const IconCheck = () => (
  <Svg size={14}>
    <circle cx="12" cy="12" r="9" />
    <path d="m8.5 12 2.5 2.5 4.5-5" />
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
