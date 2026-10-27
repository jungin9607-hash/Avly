import { Link } from "react-router-dom";
import AnalysisGate from "../common/components/AnalysisGate";
import { ROUTES } from "../../routes";
import { toReportDocument } from "./reportDocModel";
import "./ReportDoc.css";

// 인쇄·PDF 저장용 보고서. 화면(어두운 결과 화면)을 그대로 찍는 대신, 한 장짜리 문서 형식으로 다시 구성한다.
// 보여 주는 화면과 인쇄가 같은 모양이다(A4 세로). 위쪽 도구 줄은 화면에서만 보이고 인쇄에는 나오지 않는다.
export default function ReportDoc({ analysisId }) {
  return (
    <AnalysisGate analysisId={analysisId} active="분석 결과">
      {({ analysis, session }) => (
        <ReportDocView analysisId={analysisId} doc={toReportDocument(analysis.result, { analysisId, createdAt: analysis.updated_at, expiresAt: session?.expiresAt })} />
      )}
    </AnalysisGate>
  );
}

export function ReportDocView({ analysisId, doc, toolbar = true }) {
  const { headline } = doc;
  const hasRatio = headline.me != null;
  return (
    <div className="rd">
      {toolbar && (
        <div className="rd-toolbar">
          <Link to={ROUTES.report(analysisId)} className="rd-back">← 분석 결과로 돌아가기</Link>
          <span className="rd-tip">인쇄 창에서 <b>대상을 &lsquo;PDF로 저장&rsquo;</b>으로 고르면 파일로 받을 수 있어요.</span>
          <button type="button" className="rd-print" onClick={() => window.print()}>PDF로 저장 (인쇄)</button>
        </div>
      )}
      <article className="rd-page">
        <header className="rd-head">
          <p className="rd-brand">Avly 에블리</p>
          <h1>사고 분석 보고서</h1>
          <dl className="rd-meta">
            {doc.meta.code && (<><dt>분석 번호</dt><dd>{doc.meta.code}</dd></>)}
            {doc.meta.createdAt && (<><dt>분석 시각</dt><dd>{doc.meta.createdAt}</dd></>)}
            {doc.meta.expiresAt && (<><dt>자동 삭제 예정</dt><dd>{doc.meta.expiresAt}</dd></>)}
          </dl>
        </header>

        {doc.notice && <p className="rd-notice">{doc.notice}</p>}

        <section className="rd-section rd-headline" aria-label="과실 비율 요약">
          <h2>1. 한눈에 보기</h2>
          {headline.oneLine && <p className="rd-oneline">{headline.oneLine}</p>}
          <p className="rd-headline-title">{headline.title}</p>
          {hasRatio ? (
            <>
              <div className="rd-ratio-numbers"><span>내 차 <b>{headline.me}%</b></span><span>상대 차 <b>{headline.other}%</b></span></div>
              <div className="rd-bar" role="img" aria-label={`내 차 ${headline.me}%, 상대 차 ${headline.other}%`}><span style={{ width: `${headline.me}%` }} /></div>
            </>
          ) : (
            <p className="rd-none">확정할 수 있는 비율이 없어요.</p>
          )}
          {headline.note && <p className="rd-note">{headline.note}</p>}
        </section>

        <section className="rd-section">
          <h2>2. 사고는 이렇게 진행됐어요</h2>
          {doc.timeline.rows.length > 0 ? (
            <ol className="rd-story">
              {doc.timeline.rows.map((r, i) => (
                <li key={i}>
                  <p className="rd-story-head"><b>{r.label}</b><span className="rd-time">영상 {r.range}</span>{r.tag && <span className="rd-tag rd-tag-light">{r.tag}</span>}</p>
                  <p>{r.title}</p>
                </li>
              ))}
            </ol>
          ) : (
            <p className="rd-none">영상에서 사고 진행 순서를 정리하지 못했어요.</p>
          )}
          {doc.timeline.note && <p className="rd-small">{doc.timeline.note}</p>}
          {doc.timeline.rows.length > 0 && <p className="rd-small">시간은 영상이 시작된 때부터 잰 값이에요. AI가 장면에서 관찰한 구간이라 정확한 충돌 순간과는 다를 수 있어요.</p>}

          <h3>어떤 사고 유형으로 봤나요</h3>
          <table className="rd-table rd-kv">
            <tbody>{doc.situation.rows.map(([k, v]) => (<tr key={k}><th scope="row">{k}</th><td>{v}</td></tr>))}</tbody>
          </table>
          {doc.situation.official && <p className="rd-small">과실비율 인정기준 원문 표기: {doc.situation.official}</p>}
          {doc.situation.candidates.length > 0 && (
            <div className="rd-small"><b>가장 가까운 사고 유형(참고용):</b><ul>{doc.situation.candidates.map((c) => <li key={c}>{c}</li>)}</ul></div>
          )}
        </section>

        {doc.steps.length > 0 && (
          <section className="rd-section">
            <h2>3. 비율은 이렇게 나왔어요</h2>
            <ol className="rd-steps">
              {doc.steps.map((s, i) => (
                <li key={i} className={s.base ? "is-base" : ""}>
                  <div className="rd-step-text">
                    <b>{s.title}</b>
                    {s.change && <span className="rd-change">{s.change}</span>}
                    {s.detail && <p>{s.detail}</p>}
                  </div>
                  <div className="rd-step-ratio" aria-label={`내 차 ${s.me}%, 상대 차 ${s.other}%`}>
                    <span>내 차 <b>{s.me}%</b></span><span>상대 차 <b>{s.other}%</b></span>
                  </div>
                </li>
              ))}
            </ol>
            {(doc.pending.length > 0 || doc.notApplied.length > 0 || doc.answeredNo.length > 0) && (
              <div className="rd-more">
                <h3>더 확인하면 비율이 달라질 수 있어요</h3>
                {doc.pending.length > 0 && (
                  <div className="rd-small"><b>확인하지 못해서 계산에 넣지 않은 사정</b><ul>{doc.pending.map((p) => <li key={p.title}>{p.title}{p.question ? ` — ${p.question}` : ""}</li>)}</ul></div>
                )}
                {doc.notApplied.length > 0 && (
                  <div className="rd-small"><b>다른 이유로 적용하지 않은 사정</b><ul>{doc.notApplied.map((p, i) => <li key={`${p.title}-${i}`}>{p.title}{p.reason ? ` — ${p.reason}` : ""}</li>)}</ul></div>
                )}
                {doc.answeredNo.length > 0 && (
                  <p className="rd-small"><b>해당 없다고 답한 사정({doc.answeredNo.length}개)</b> {doc.answeredNo.join(" / ")}</p>
                )}
              </div>
            )}
          </section>
        )}

        <section className="rd-section">
          <h2>4. 비슷한 판례 (참고)</h2>
          {doc.cases.length === 0 && <p className="rd-none">연결된 판례가 없어요.</p>}
          {doc.cases.map((c) => (
            <div className="rd-case" key={c.heading}>
              {c.summary && <p className="rd-case-summary">{c.summary}</p>}
              {c.common.length > 0 && <p className="rd-pair"><b className="rd-same">비슷한 점</b> {c.common.join(" ")}</p>}
              {c.differences.length > 0 && <p className="rd-pair"><b className="rd-diff">다른 점</b> {c.differences.join(" ")}</p>}
              <p className="rd-small rd-source">
                {c.heading}{c.matchLabel && <span className="rd-tag">{c.matchLabel}</span>}{c.unverified && <span className="rd-tag rd-tag-light">검수 전</span>}
                {" · "}{c.category}{c.byAi ? " · 비교는 AI가 정리했어요" : ""}{c.limit ? ` · ${c.limit}` : ""}
              </p>
            </div>
          ))}
          <p className="rd-small">판례는 같은 과실 비율이 나온다는 뜻이 아니에요. 사실관계가 다르면 결과도 달라져요.</p>
        </section>

        {doc.laws.length > 0 && (
          <section className="rd-section">
            <h2>5. 관련 법령</h2>
            <ul className="rd-laws">{doc.laws.map((l) => (<li key={l.name}><b>{l.name}</b><br />{l.easy}</li>))}</ul>
          </section>
        )}

        <section className="rd-section rd-closing">
          <h2>유의사항과 출처</h2>
          <ul>
            <li>이 보고서는 <b>법적 효력이 없는 AI 참고 자료</b>예요. 실제 과실 비율을 확정하지 않으며, 최종 판단은 보험사 합의나 법원 판결에 따라 달라져요.</li>
            <li>손해보험협회 인정기준의 <b>기본 비율</b>에 비율이 달라지는 사정을 더하거나 빼서 계산했어요. 영상을 올린 블랙박스 차량을 &lsquo;내 차&rsquo;로 보고 분석했어요.</li>
            <li>AI는 영상의 일부 장면만 보고 판단해서 사고 유형, 움직임, 접촉 여부가 틀릴 수 있어요. 번호판과 사람을 자동으로 가린 뒤 외부 AI 서비스로 보냈는데, 가리는 방식은 완전하지 않아요.</li>
            <li>판례와 법령 풀이는 참고용이에요. &lsquo;검수 전&rsquo; 자료는 사람이 아직 확인하지 않았어요.</li>
            {doc.meta.expiresAt && <li>이 분석 결과는 {doc.meta.expiresAt}에 서버에서 삭제돼요. PDF로 저장한 파일은 내 기기에 남아요.</li>}
            <li>근거 자료: {doc.sources.join(", ")}.</li>
          </ul>
        </section>
        <footer className="rd-foot">에블리 · 분석 번호 {doc.meta.code} · 법적 효력 없는 AI 참고 자료</footer>
      </article>
    </div>
  );
}
