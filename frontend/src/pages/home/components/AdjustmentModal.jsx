import { useState } from "react";
import ModalShell from "./ModalShell";

// 4단계: 고른 사고 유형에 등록된 가감요소를 쉬운 말 질문으로 묻는다.
//   영상에서 관찰·추정한 것은 AI 제안을 보여 주고 미리 골라 둔다. 사용자의 답이 항상 우선한다.
//   답하지 않은 항목은 '잘 모르겠어요'로 보내고, 서버는 이를 0으로 확정하지 않고 '미확인'으로 둔다.
export default function AdjustmentModal({ option, questions, onSubmit, onBack, onClose }) {
  const [answers, setAnswers] = useState(() => Object.fromEntries(questions.filter((q) => q.suggested).map((q) => [q.key, q.suggested.answer])));
  const send = () => onSubmit(Object.fromEntries(questions.map((q) => [q.key, answers[q.key] ?? "잘 모르겠어요"])));

  return (
    <ModalShell
      title={questions.some((q) => q.pdf_source) ? "PDF 가감요소를 확인해 주세요" : "과실 비율에 영향을 주는 상황을 확인해 주세요"}
      desc={`기본 비율은 내 차 ${option.base_me}% : 상대 차 ${option.base_other}%예요. 아래 상황이 있었다면 비율이 달라져요. 모르는 항목은 '잘 모르겠어요'를 골라도 돼요.`}
      progress={[4, 4]}
      onClose={onClose}
    >
      {questions.some((q) => q.pdf_source) && (
        <p className="md-hint" style={{ padding: "0 30px" }}>
          사고 유형별 원문 가감요소 · {[...new Set(questions.map((q) => q.pdf_source?.chart).filter(Boolean))].join(" / ")} · 2023.06 기준
        </p>
      )}
      <form onSubmit={(event) => { event.preventDefault(); send(); }}>
        <div className="md-body">
          <ol className="md-questions">
            {questions.map((q, index) => (
              <li key={q.key}>
                <fieldset>
                  <legend>
                    <span className="md-qnum">{index + 1}</span>
                    {q.pdf_source ? `${q.who} · ${q.pdf_factor || q.title}` : q.question}
                  </legend>
                  {!q.pdf_source && <p className="md-q-easy">{q.easy}</p>}
                  {q.registry_note && <p className="md-hint">{q.registry_note}</p>}
                  <p className="md-q-effect">예라면 → {q.effect}</p>
                  {q.pdf_source && (
                    <>
                      <p className="md-hint">PDF 원문: {q.pdf_source.raw_text} · {q.pdf_source.chart}</p>
                      <details className="md-hint"><summary>항목 설명</summary><p>{q.easy}</p></details>
                    </>
                  )}
                  {q.needs_user && !q.pdf_source && <p className="md-hint">실제 사고에 해당한 상황인지 직접 확인해 주세요.</p>}
                  {q.suggested && (
                    <p className="md-suggest">
                      AI 제안: <b>{q.suggested.answer}</b> ({q.suggested.basis}
                      {q.suggested.evidence ? ` · ${q.suggested.evidence}` : ""})
                    </p>
                  )}
                  <div className="md-options" style={{ "--cols": 3 }}>
                    {q.options.map((choice) => (
                      <label key={choice} className={answers[q.key] === choice ? "md-option is-on" : "md-option"}>
                        <input
                          type="radio"
                          name={q.key}
                          value={choice}
                          checked={answers[q.key] === choice}
                          onChange={() => setAnswers((current) => ({ ...current, [q.key]: choice }))}
                        />
                        <span className="md-radio" aria-hidden="true" />
                        {choice}
                      </label>
                    ))}
                  </div>
                </fieldset>
              </li>
            ))}
          </ol>
        </div>
        <footer className="md-foot md-foot-row">
          <button type="button" className="md-btn-ghost" onClick={onBack}>
            이전
          </button>
          <button type="submit" className="md-btn">
            결과 보기
            <span aria-hidden="true">→</span>
          </button>
        </footer>
      </form>
    </ModalShell>
  );
}
