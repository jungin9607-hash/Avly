import Icon from "../../components/ui/Icon";

const STEP_LABELS = ["동의", "분석", "질문", "상황 결과"];

export function StepIndicator({ current }) {
  return (
    <div className="step-indicator">
      {STEP_LABELS.map((label, index) => {
        const number = index + 1;
        const state =
          current === number ? "step-active" : current > number ? "step-complete" : "";

        return (
          <div className="step-wrapper" key={number}>
            <span className={`step-badge ${state}`}>
              {number}. {label}
            </span>
            {number !== STEP_LABELS.length && <span className="step-arrow">›</span>}
          </div>
        );
      })}
    </div>
  );
}

export function QuestionCard({ number, question, children }) {
  return (
    <div className="question-card">
      <strong className="question-title">
        <span>{number}</span>
        {question}
      </strong>
      <div className="radio-grid">{children}</div>
    </div>
  );
}

export function RadioOption({ name, checked, onChange, label }) {
  return (
    <label className={`radio-option ${checked ? "radio-selected" : ""}`}>
      <input type="radio" name={name} checked={checked} onChange={onChange} />
      <span>{label}</span>
    </label>
  );
}

export function Milestone({ number, text, done }) {
  return (
    <div className={`milestone ${done ? "milestone-done" : ""}`}>
      <div>
        <Icon name={done ? "check_circle" : "schedule"} />
        <span>
          {number}. {text}
        </span>
      </div>
      <span className="milestone-status">{done ? "완료" : "대기"}</span>
    </div>
  );
}

export function ReanalyzeOption({ checked, onChange, title, description }) {
  return (
    <label className={`reanalyze-option ${checked ? "reanalyze-selected" : ""}`}>
      <input type="radio" name="reanalyze" checked={checked} onChange={onChange} />
      <div>
        <strong>{title}</strong>
        <p>{description}</p>
      </div>
    </label>
  );
}
