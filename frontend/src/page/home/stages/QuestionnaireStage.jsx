import { useState } from "react";
import { QuestionCard, RadioOption } from "../ModalParts";
import { INITIAL_ANSWERS, QUESTIONS } from "../constants";

function QuestionnaireStage({ onSubmit }) {
  const [answers, setAnswers] = useState(INITIAL_ANSWERS);

  return (
    <div className="modal-stage">
      <div>
        <h3>정확한 분석을 위한 추가 질문</h3>
      </div>

      {QUESTIONS.map((question, index) => (
        <QuestionCard key={question.key} number={String(index + 1)} question={question.text}>
          {question.options.map((option) => (
            <RadioOption
              key={option.value}
              name={question.key}
              checked={answers[question.key] === option.value}
              onChange={() =>
                setAnswers((prev) => ({ ...prev, [question.key]: option.value }))
              }
              label={option.label}
            />
          ))}
        </QuestionCard>
      ))}

      <button type="button" className="modal-primary-button" onClick={onSubmit}>
        답변 제출하고 재분석 하기
      </button>
    </div>
  );
}

export default QuestionnaireStage;
