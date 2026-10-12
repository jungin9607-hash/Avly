import { useState } from "react";
import ModalShell from "./ModalShell";

const QUESTIONS = [
  {
    key: "signal",
    text: "충돌 직전 상대 차량이 방향지시등(깜빡이)을 점등했나요?",
    options: ["켜지 않았다", "켜져 있었다", "인지하지 못함"],
  },
  {
    key: "speed",
    text: "내 차량은 정상 차로에서 제한속도(50km/h)를 준수 중이었나요?",
    options: ["규정속도 준수 (50km/h 이하)", "규정속도 초과 (+10km/h 이상)"],
  },
  {
    key: "visibility",
    text: "사고 당시 야간·우천 등 시야 장애 요인이 있었나요?",
    options: ["맑음 (주간 시야 확보)", "야간 또는 우천·안개 (시야 불량)"],
  },
];

/* 2단계: 현장 정황 확인 질문 (각 문항 첫 번째 답이 기본 선택) */
export default function QuestionModal({ onSubmit, onClose }) {
  const [answers, setAnswers] = useState(() => Object.fromEntries(QUESTIONS.map((q) => [q.key, q.options[0]])));

  return (
    <ModalShell
      badge={
        <>
          <IconChecklist />
          현장 정황 교차 검증 (질문 3문항)
        </>
      }
      title="정확한 과실 분석을 위한 추가 질문"
      desc="영상 판독 신뢰도를 높이기위해 운전자가 인지한 현장 상황을 체크해 주세요."
      progress={[2, 2]}
      onClose={onClose}
    >
      <div className="md-body">
        <ol className="md-questions">
          {QUESTIONS.map((q, i) => (
            <li key={q.key}>
              <fieldset>
                <legend>
                  <span className="md-qnum">{i + 1}</span>
                  {q.text}
                </legend>
                <div className="md-options" style={{ "--cols": q.options.length }}>
                  {q.options.map((opt) => (
                    <label key={opt} className={answers[q.key] === opt ? "md-option is-on" : "md-option"}>
                      <input
                        type="radio"
                        name={q.key}
                        value={opt}
                        checked={answers[q.key] === opt}
                        onChange={() => setAnswers((prev) => ({ ...prev, [q.key]: opt }))}
                      />
                      <span className="md-radio" aria-hidden="true" />
                      {opt}
                    </label>
                  ))}
                </div>
              </fieldset>
            </li>
          ))}
        </ol>
      </div>

      <footer className="md-foot">
        <button type="button" className="md-btn md-btn-wide" onClick={() => onSubmit(answers)}>
          답변 제출하고 AI 영상 정밀 분석 시작하기
          <span aria-hidden="true">→</span>
        </button>
      </footer>
    </ModalShell>
  );
}

const IconChecklist = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.9"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <rect x="4" y="3" width="16" height="18" rx="2" />
    <path d="m8 9 1.5 1.5L12 8M8 15l1.5 1.5L12 14M14.5 9.5H17M14.5 15.5H17" />
  </svg>
);
