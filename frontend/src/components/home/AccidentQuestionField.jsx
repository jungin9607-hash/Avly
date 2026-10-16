export default function AccidentQuestionField({ question, number, value, onChange }) {
  return (
    <fieldset>
      <legend>
        <span className="md-qnum">{number}</span>
        {question.text}
      </legend>
      <div className="md-options" style={{ "--cols": 2 }}>
        {question.options.map((option) => (
          <label key={option} className={value === option ? "md-option is-on" : "md-option"}>
            <input
              type="radio"
              name={question.key}
              value={option}
              checked={value === option}
              onChange={() => onChange(question.key, option)}
              required
            />
            <span className="md-radio" aria-hidden="true" />
            {option}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
