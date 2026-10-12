import { useState } from "react";
import ModalShell from "./ModalShell";

const ITEMS = [
  {
    key: "analysis",
    title: "교통사고 과실 산정을 위한 영상 수집 및 AI 영상 분석 처리 동의",
    body: "블랙박스 프레임 분석, 차선 및 객체 추적, 손해보험협회 인정기준 및 판례 데이터셋 대조를 위한 일시적 영상 전송 및 비전 추론 처리에 동의합니다.",
  },
  {
    key: "quiz",
    title: "사고 예방 퀴즈 사용 동의",
    body: "차량 번호판 및 보행자 얼굴 등 민감 식별정보를 AI 블러링(비식별화) 처리한 후, 운전자 안전의식 고취를 위한 '사고 예방 퀴즈' 및 안전운전 AI 알고리즘 고도화에 기여합니다.",
  },
];

/* 1단계: 영상 수집 동의
 * 모든 항목은 선택 사항: 동의하지 않아도 다음 단계로 넘어갈 수 있음 */
export default function ConsentModal({ fileNames, onStart, onClose, onSimulateUnsupported, onPickAnother }) {
  const [agreed, setAgreed] = useState({ analysis: false, quiz: false });
  const [blocked, setBlocked] = useState(false); // "분석 불가 사고" 시뮬레이션 화면

  const allAgreed = ITEMS.every((it) => agreed[it.key]);
  const toggleAll = () => setAgreed(Object.fromEntries(ITEMS.map((it) => [it.key, !allAgreed])));
  const toggle = (key) => setAgreed((prev) => ({ ...prev, [key]: !prev[key] }));

  if (blocked) {
    return (
      <ModalShell
        badge={
          <>
            <IconAlert />
            분석 불가
          </>
        }
        title="분석할 수 없는 사고 영상이에요"
        desc="사고 장면이 충분히 담기지 않았거나 화면이 어두워 과실을 판단하기 어려워요. 영상 가이드를 확인한 뒤 다른 영상을 올려 주세요."
        onClose={onClose}
      >
        <footer className="md-foot md-foot-row">
          <button type="button" className="md-btn-ghost" onClick={() => setBlocked(false)}>
            동의 화면으로 돌아가기
          </button>
          <button type="button" className="md-btn" onClick={onPickAnother}>
            다른 영상 선택
          </button>
        </footer>
      </ModalShell>
    );
  }

  return (
    <ModalShell
      badge={
        <>
          <IconShield />
          개인정보 암호화 및 법률 준수
        </>
      }
      title="블랙박스 영상 수집 동의"
      desc="에블리는 의뢰인의 영상 데이터를 엄격한 보안 프로토콜 하에 분석하며, 정확한 과실 도출과 공익적 교통안전 연구를 위해 아래 항목의 동의가 필요합니다."
      progress={[1, 2]}
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
          전체 항목 동의(선택)
        </label>

        <ul className="md-items">
          {ITEMS.map((it) => (
            <li key={it.key}>
              <label className={agreed[it.key] ? "md-item is-on" : "md-item"}>
                <input type="checkbox" checked={agreed[it.key]} onChange={() => toggle(it.key)} />
                <span className="md-check" aria-hidden="true" />
                <span className="md-item-text">
                  <span className="md-item-title">
                    <em>선택</em>
                    {it.title}
                  </span>
                  <span className="md-item-body">{it.body}</span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      </div>

      <footer className="md-foot">
        <button type="button" className="md-btn md-btn-wide" onClick={() => onStart(agreed)}>
          {allAgreed ? "동의하고 영상 분석 시작하기" : "영상 분석 시작하기"}
          <span aria-hidden="true">→</span>
        </button>

        <div className="md-sim">
          <span className="md-sim-label">예외 상황 시뮬레이션:</span>
          <button type="button" onClick={onSimulateUnsupported}>
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
const IconShield = () => (
  <Svg size={14}>
    <path d="M12 3 5 6v5c0 4.5 3 8.5 7 10 4-1.5 7-5.5 7-10V6z" />
    <path d="m9.5 12 2 2 3.5-4" />
  </Svg>
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
