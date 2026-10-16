import ModalShell from "./ModalShell";
import AccidentQuestionField from "./AccidentQuestionField";
import { QUESTION_STEPS } from "./accidentQuestions";

export default function QuestionModal({ stage, answers, onAnswerChange, onSubmit, onBack, onClose }) {
  const content = QUESTION_STEPS[stage];

  return (
    <ModalShell
      title={content.title}
      desc={content.description}
      progress={[stage + 2, 5]}
      onClose={onClose}
    >
      <form onSubmit={(event) => { event.preventDefault(); onSubmit(); }}>
        <div className="md-body">
          <ol className="md-questions">
            {content.questions.map((question, index) => (
              <li key={question.key}>
                <AccidentQuestionField
                  question={question}
                  number={index + 1}
                  value={answers[question.key]}
                  onChange={onAnswerChange}
                />
              </li>
            ))}
          </ol>
        </div>
        <footer className="md-foot md-foot-row">
          {onBack && <button type="button" className="md-btn-ghost" onClick={onBack}>이전 질문</button>}
          <button type="submit" className="md-btn">
            {content.submitLabel}
            <span aria-hidden="true">→</span>
          </button>
        </footer>
      </form>
    </ModalShell>
  );
}
