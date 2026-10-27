import ConsentModal from "./ConsentModal";
import AnalysisProgressModal from "./AnalysisProgressModal";
import SituationConfirmModal from "./SituationConfirmModal";
import AdjustmentModal from "./AdjustmentModal";
import NoticeModal from "./NoticeModal";

/* ---------- 단계별 팝업 ---------- */
export default function FlowModals({ file, started, flow, onBegin, onClose, onPickAnother, onChoose, onConfirm, onCancel, onBack }) {
  if (!started) return <ConsentModal fileName={file?.name} onStart={onBegin} onClose={onClose} onPickAnother={onPickAnother} />;
  switch (flow.phase) {
    case "uploading":
      return <AnalysisProgressModal phase="uploading" progress={flow.progress} onClose={onClose} />;
    case "analyzing":
      return <AnalysisProgressModal phase="analyzing" stage={flow.stage} onClose={onClose} onCancel={onCancel} />;
    case "finalizing":
    case "done":
      return <AnalysisProgressModal phase="finalizing" onClose={onClose} />;
    case "confirming":
      return <SituationConfirmModal situation={flow.situation} items={flow.catalog} onChoose={onChoose} onClose={onClose} />;
    case "adjusting":
      return <AdjustmentModal option={flow.option} questions={flow.questions} heldBack={flow.heldBack} onSubmit={(answers) => onConfirm(flow.option, answers)} onBack={onBack} onClose={onClose} />;
    case "unsupported":
      return (
        <NoticeModal
          title="분석할 수 없는 영상입니다"
          desc={flow.unsupportedReason}
          primary={{ label: "다른 영상 올리기", onClick: onPickAnother }}
          secondary={{ label: "닫기", onClick: onClose }}
        >
          <p className="md-hint">에블리는 지금 차량끼리 부딪힌 사고(차대차)만 분석할 수 있습니다. 보행자, 이륜차, 자전거 사고는 보험사나 전문가에게 상담해 주시기 바랍니다. 올리신 영상은 저장에 동의하셨더라도 하루 안에 삭제됩니다.</p>
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
  VIDEO_TOO_LONG: { title: "영상이 너무 깁니다", hint: "사고 전후 구간만 잘라서 다시 올려 주시기 바랍니다." }, // 서버 메시지에 길이 기준(최대 20초)이 들어 있다
  AI_NOT_CONFIGURED: { title: "분석 서비스를 준비하고 있습니다", hint: "지금은 분석을 시작할 수 없습니다. 잠시 후 다시 시도해 주시기 바랍니다." },
  CANCELLED: { title: "분석을 취소했습니다", hint: "같은 영상이든 다른 영상이든 다시 분석할 수 있습니다." },
  SESSION_EXPIRED: { title: "보관 시간이 지났습니다", hint: "분석 결과와 영상은 일정 시간이 지나면 자동으로 삭제됩니다. 새 영상으로 다시 분석해 주시기 바랍니다." },
  NETWORK_ERROR: { title: "서버에 연결하지 못했습니다", hint: "인터넷 연결을 확인하고 다시 시도해 주시기 바랍니다." },
  FILE_TOO_LARGE: { title: "영상 용량이 너무 큽니다", hint: "용량을 줄이거나 사고 전후 구간만 잘라서 올려 주시기 바랍니다." },
  UNSUPPORTED_FILE_TYPE: { title: "지원하지 않는 영상 형식입니다", hint: "MP4, MOV, AVI 영상만 올릴 수 있습니다." },
};

function FailedNotice({ error, onPickAnother, onClose }) {
  const known = FAILURE[error?.code];
  return (
    <NoticeModal
      title={known?.title ?? "분석하지 못했습니다"}
      desc={error?.message}
      primary={{ label: "다른 영상 선택", onClick: onPickAnother }}
      secondary={{ label: "닫기", onClick: onClose }}
    >
      {known && <p className="md-hint">{known.hint}</p>}
    </NoticeModal>
  );
}
