import { useState } from "react";
import ModalShell from "./ModalShell";

const ITEMS = [
  {
    key: "analysis",
    title: "교통사고 과실 산정을 위한 영상 수집 및 AI 영상 분석 처리 동의",
    body: "블랙박스 프레임 분석, 차선 및 객체 추적, 손해보험협회 인정기준 및 판례 데이터셋 대조를 위한 일시적 영상 전송 및 비전 추론 처리에 동의합니다.",
  },
];

/* 1단계: 영상 수집 동의
 * 분석 동의는 필수: 동의해야 영상 분석을 시작할 수 있음 */
export default function ConsentModal({ fileNames, onStart, onClose, onPickAnother }) {
  const [agreed, setAgreed] = useState({ analysis: false });
  const [blocked, setBlocked] = useState(false); // "분석 불가 사고" 시뮬레이션 화면
  const [unsupported, setUnsupported] = useState(false);

  const allAgreed = ITEMS.every((it) => agreed[it.key]);
  const toggleAll = () => setAgreed(Object.fromEntries(ITEMS.map((it) => [it.key, !allAgreed])));

  if (blocked) {
    return (
      <ModalShell
        title="분석할 수 없는 사고 영상이에요"
        desc="사고 장면이 충분히 담기지 않았거나 화면이 어두워 과실을 판단하기 어려워요. 영상 가이드를 확인한 뒤 다른 영상을 올려 주세요."
        onClose={onClose}
      >
        <footer className="md-foot md-foot-row">
          <button type="button" className="md-btn" onClick={onPickAnother}>
            다른 영상 선택
          </button>
          <button type="button" className="md-btn-ghost" onClick={onClose}>
            취소
          </button>
        </footer>
      </ModalShell>
    );
  }

  if (unsupported) {
    return (
      <ModalShell
        title="지원하지 않는 영상 파일이에요"
        desc="MP4, MOV, AVI 형식의 영상만 분석할 수 있어요. 지원되는 형식의 영상을 선택해 주세요."
        onClose={onClose}
      >
        <footer className="md-foot md-foot-row">
          <button type="button" className="md-btn" onClick={onPickAnother}>
            다른 영상 선택
          </button>
          <button type="button" className="md-btn-ghost" onClick={onClose}>
            취소
          </button>
        </footer>
      </ModalShell>
    );
  }

  return (
    <ModalShell
      title="블랙박스 영상 수집 동의"
      progress={[1, 5]}
      onClose={onClose}
    >
      <div className="md-body">
        {fileNames.length > 0 && (
          <p className="md-file">
            <IconVideo />
            <span>{fileNames.length === 1 ? fileNames[0] : `${fileNames[0]} 외 ${fileNames.length - 1}개`}</span>
          </p>
        )}

        <label className={allAgreed ? "md-all is-on" : "md-all"}>
          <input type="checkbox" checked={allAgreed} onChange={toggleAll} />
          <span className="md-check" aria-hidden="true" />
          위 내용에 동의합니다 (필수)
        </label>

        <ul className="md-items">
          {ITEMS.map((it) => (
            <li key={it.key}>
              <div className="md-item">
                <span className="md-item-text">
                  <span className="md-item-title">
                    {it.title}
                  </span>
                  <span className="md-item-body">{it.body}</span>
                </span>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <footer className="md-foot">
        <button type="button" className="md-btn md-btn-wide" disabled={!allAgreed} onClick={() => onStart(agreed)}>
          동의하고 영상 분석 시작하기
          <span aria-hidden="true">→</span>
        </button>

        <div className="md-sim">
          <span className="md-sim-label">예외 상황 시뮬레이션:</span>
          <button type="button" onClick={() => setUnsupported(true)}>
            <IconAlert />
            지원하지 않는 파일 테스트
          </button>
          <i aria-hidden="true" />
          <button type="button" onClick={() => setBlocked(true)}>
            <IconCar />
            분석 불가 사고 테스트
          </button>
        </div>
      </footer>
    </ModalShell>
  );
}

const Svg = ({ children, size = 16 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.9"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);
const IconVideo = () => (
  <Svg>
    <rect x="3" y="6" width="13" height="12" rx="2" />
    <path d="m16 10 5-3v10l-5-3" />
  </Svg>
);
const IconAlert = () => (
  <Svg size={14}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7.5v5M12 16h.01" />
  </Svg>
);
const IconCar = () => (
  <Svg size={14}>
    <path d="M5 16V11l2-5h10l2 5v5" />
    <path d="M3 16h18v3H3zM5 11h14" />
    <path d="M7 19v2M17 19v2" />
  </Svg>
);
