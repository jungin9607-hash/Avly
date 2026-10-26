import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import TopNav from "../common/components/TopNav";
import FlowModals from "./components/FlowModals";
import NoticeModal from "./components/NoticeModal";
import ResumeBanner from "./components/ResumeBanner";
import GuideTiles from "./components/GuideTiles";
import UploadDrop from "./components/UploadDrop";
import { IconShield } from "./components/icons";
import { ROUTES } from "../../routes";
import ReportPageLink from "./components/ReportPageLink";
import useAnalysisFlow from "./hooks/useAnalysisFlow";
import "./Home.css";

const ACCEPT_EXT = ["mp4", "mov", "avi"];
const MAX_MB = 50;
const IN_PROGRESS = ["uploading", "analyzing", "confirming", "adjusting", "finalizing"];

// 나가려 할 때 단계별로 알려 줄 말
const LEAVE_HINT = {
  uploading: "지금 나가면 업로드가 멈춰요. 처음부터 다시 올려야 해요.",
  analyzing: "분석은 서버에서 계속돼요. 끝나면 이 화면의 '진행 중인 분석'이나 상단 메뉴의 '분석 결과'에서 이어서 확인할 수 있어요.",
  finalizing: "결과 계산은 서버에서 계속돼요. 끝나면 상단 메뉴의 '분석 결과'에서 볼 수 있어요.",
  confirming: "분석은 이미 끝났어요. 나가면 고르던 내용은 사라지지만, '진행 중인 분석'에서 다시 이어서 확인할 수 있어요. 영상을 다시 분석하지는 않아요.",
  adjusting: "분석은 이미 끝났어요. 나가면 답하던 내용은 사라지지만, '진행 중인 분석'에서 처음부터 다시 이어서 확인할 수 있어요. 영상을 다시 분석하지는 않아요.",
};

export default function Home() {
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [pending, setPending] = useState([]); // 동의 팝업을 기다리는 선택된 영상
  const [started, setStarted] = useState(false); // 동의하고 분석을 시작했는지
  const [leaving, setLeaving] = useState(false); // 진행 중인 팝업을 닫으려 할 때 나가도 되는지 묻는 중
  const [params] = useSearchParams();
  const resumeId = params.get("resume"); // 결과 화면에서 "이어서 확인하기"로 들어온 분석 번호
  const { state: flow, start, choose, confirm, cancel, back, reset } = useAnalysisFlow(resumeId);

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

  // 진행 중인 팝업은 바로 닫지 않고 먼저 물어본다. 닫아도 서버 분석은 계속되지만, 고르던 내용은 사라진다.
  const requestClose = () => {
    if (IN_PROGRESS.includes(flow.phase)) setLeaving(true);
    else closeAll();
  };

  const leave = () => {
    setLeaving(false);
    closeAll();
  };

  const pickAnother = () => {
    closeAll();
    inputRef.current.click();
  };

  const begin = ({ retention, place }) => {
    setStarted(true);
    start(pending[0], retention, place);
  };

  // 팝업의 "결과 보기"로 분석이 끝나면 결과 화면으로 이동한다
  useEffect(() => {
    if (flow.phase === "done") navigate(ROUTES.report(flow.analysisId));
  }, [flow.phase, flow.analysisId, navigate]);

  return (
    <div className="uh">
      <TopNav active="홈" theme="clear" />

      {/* 주요 부분: 네이비 배경 위에 업로드와 가이드 */}
      <section className="uh-hero">
        <div className="uh-grid">
          {/* 위: 단계 · 제목 · 진행 중인 분석 */}
          <div className="uh-intro">
            <ol className="uh-steps" aria-label="분석 단계">
              <li className="on">영상 업로드</li>
              <li>AI 분석</li>
              <li>결과 확인</li>
            </ol>
            <h1>블랙박스 영상 분석</h1>
            {flow.phase === "idle" && pending.length === 0 && <ResumeBanner />}
          </div>

          {/* 아래 왼쪽: 업로드 상자 / 오른쪽: 영상 가이드 타일 3개 */}
          <UploadDrop inputRef={inputRef} error={error} maxMb={MAX_MB} onFiles={selectFiles} />
          <GuideTiles />
        </div>
      </section>

      <main className="uh-main">
        <div className="uh-footer">
          <ReportPageLink />
          <footer className="uh-notice">
            <IconShield />
            <p>
              에블리는 손해보험협회 과실비율 인정기준과 판례 요약을 참고해 과실 비율을 안내하는 AI 참고 서비스입니다.
              확정한 비율이 아니며 법적 효력이 없고, 최종 판단은 보험사 합의나 법원 판결에 따릅니다.
            </p>
          </footer>
        </div>
      </main>

      {/* 영상 선택 → 수집 동의 → 업로드·분석 → 사고 상황 확인 → 가감요소 질문 → 결과 */}
      {leaving && (
        <NoticeModal
          title="창을 닫을까요?"
          desc={LEAVE_HINT[flow.phase]}
          primary={{ label: "계속 보기", onClick: () => setLeaving(false) }}
          secondary={{ label: "나가기", onClick: leave }}
          onClose={() => setLeaving(false)}
          sticky
        />
      )}
      {!leaving && flow.phase !== "done" && (pending.length > 0 || flow.phase !== "idle") && (
        <FlowModals
          file={pending[0]}
          started={started || flow.phase !== "idle"}
          flow={flow}
          onBegin={begin}
          onClose={requestClose}
          onPickAnother={pickAnother}
          onChoose={choose}
          onConfirm={confirm}
          onCancel={cancel}
          onBack={back}
        />
      )}
    </div>
  );
}
