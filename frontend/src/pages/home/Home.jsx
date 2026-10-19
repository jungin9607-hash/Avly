import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import TopNav from "../common/components/TopNav";
import FlowModals from "./components/FlowModals";
import GuideTiles from "./components/GuideTiles";
import UploadDrop from "./components/UploadDrop";
import { IconShield } from "./components/icons";
import { ROUTES } from "../../routes";
import ReportPageLink from "./components/ReportPageLink";
import useAnalysisFlow from "./hooks/useAnalysisFlow";
import "./Home.css";

const ACCEPT_EXT = ["mp4", "mov", "avi"];
const MAX_MB = 50;

export default function Home() {
  const inputRef = useRef(null);
  const navigate = useNavigate();
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

            <UploadDrop inputRef={inputRef} error={error} onFiles={selectFiles} />
          </div>

          {/* 오른쪽: 영상 가이드 타일 3개 */}
          <GuideTiles />
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
