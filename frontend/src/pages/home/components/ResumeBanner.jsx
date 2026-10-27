import { Link } from "react-router-dom";
import useAnalysis from "../../../api/useAnalysis";
import { lastAnalysisId } from "../../../api/session";
import { ROUTES } from "../../../routes";
import "./ResumeBanner.css";

// 이 브라우저에서 만든 가장 최근 분석이 아직 끝나지 않았다면(분석 중이거나 사용자의 확인을 기다리는 중) 이어서 볼 수 있게 알려 준다.
// 팝업을 닫거나 새로고침해도 서버는 분석을 계속하므로, 돌아올 길을 눈에 보이게 둔다.
const TEXT = {
  queued: { title: "분석이 곧 시작됩니다", action: "진행 상황 보기" },
  processing: { title: "영상을 분석하고 있습니다", action: "진행 상황 보기" },
  awaiting_confirmation: { title: "분석이 끝났습니다. 사고 상황을 확인해 주시기 바랍니다", action: "이어서 확인하기" },
};

export default function ResumeBanner() {
  const id = lastAnalysisId();
  const { analysis } = useAnalysis(id);
  const text = id && analysis ? TEXT[analysis.status] : null;
  if (!text) return null;
  return (
    <Link to={ROUTES.resume(id)} className="uh-resume" role="status" title={text.title} aria-label={`진행 중인 분석: ${text.title}. ${text.action}`}>
      <span className="uh-resume-label">진행 중인 분석</span>
      <span className="uh-resume-action">
        {text.action}
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="m9 6 6 6-6 6" />
        </svg>
      </span>
    </Link>
  );
}
