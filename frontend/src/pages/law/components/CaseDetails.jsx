// "상세 보기"를 펼치면 나오는 판례 설명: (AI 가 정리한 사건 개요 · 법원 판단 요지 · 관련 조문) → 요약 → 이 판례를 그대로 적용하기 어려운 점 → 출처
// AI 설명은 판결문에서 인용한 구절이 있는 것만 보여 준다. 판례 본문이 없으면(AI 를 쓰지 못했거나 등록 판례) 요약과 출처만 보여 준다.
// open: 펼침 여부 (닫혀 있어도 그려 두고 높이만 0으로 접어, 펼칠 때 부드럽게 내려옴)
export default function CaseDetails({ item, open }) {
  return (
    <div className={`law-details-collapse${open ? " is-open" : ""}`} inert={!open}>
      <div className="law-details-clip">
        {/* 읽는 영역이라 눌러도 카드 선택(on/off)이 바뀌지 않게 */}
        <div className="law-case-details" onClick={(e) => e.stopPropagation()}>
          {item.digest && <DigestSections digest={item.digest} />}

          <DetailSection title="판례 요약">
            <p className="law-details-overview">{item.summary}</p>
          </DetailSection>

          {item.limit && (
            <DetailSection title="내 사고에 그대로 적용하기 어려운 점">
              <p className="law-details-overview">{item.limit}</p>
            </DetailSection>
          )}

          <DetailSection title="출처">
            <p className="law-details-overview">
              {item.category}
              {item.verified ? " · 검수됨" : " · 검수 전 (사람이 확인하지 않은 자료예요)"}
              {item.caseNumber && ` · 사건번호 ${item.caseNumber}`}
            </p>
            {item.sourceUrl && (
              <p className="law-details-source">
                <a href={item.sourceUrl} target="_blank" rel="noreferrer">
                  출처 열기
                </a>
              </p>
            )}
          </DetailSection>

          {item.note && <p className="law-details-source">{item.note}</p>}
        </div>
      </div>
    </div>
  );
}

// AI 가 판례 본문을 읽고 정리한 부분: 사건 개요, 법원이 판단한 요지, 본문에 나온 도로교통법 조문. 인용한 판결문 구절을 함께 보여 준다.
function DigestSections({ digest }) {
  return (
    <>
      <p className="law-ai-badge">AI가 판례 본문을 읽고 정리했어요. 판결문에서 가져온 구절을 함께 보여 드려요.</p>
      {digest.overview && (
        <DetailSection title="사건 개요">
          <p className="law-details-overview">{digest.overview.text}</p>
          <Quote text={digest.overview.quote} />
        </DetailSection>
      )}
      {digest.points.length > 0 && (
        <DetailSection title="법원이 판단한 요지">
          <ul className="law-details-points">
            {digest.points.map((point) => (
              <li key={point.text}>
                <p>{point.text}</p>
                <Quote text={point.quote} />
              </li>
            ))}
          </ul>
        </DetailSection>
      )}
      {digest.laws.length > 0 && (
        <DetailSection title="판결문에 나온 도로교통법 조문">
          <ul className="law-details-points">
            {digest.laws.map((law) => (
              <li key={law.label}>
                <p>
                  <strong>{law.name || law.label}</strong>
                </p>
                {law.easy && <p className="law-details-law-easy">{law.easy}</p>}
              </li>
            ))}
          </ul>
        </DetailSection>
      )}
    </>
  );
}

export function Quote({ text }) {
  return text ? <p className="law-quote">판결문 “{text}”</p> : null;
}

// 소제목(왼쪽 블루 점) + 내용, 위쪽 옅은 구분선
function DetailSection({ title, children }) {
  return (
    <section className="law-details-section">
      <h4>{title}</h4>
      {children}
    </section>
  );
}

// 블루 체크 표시 (원 없이 체크만, 글자 "✓"는 글꼴 기준선 때문에 아래로 처져서 SVG로 그려 가운데에 맞춤)
export function CheckIcon({ className = "law-check" }) {
  return (
    <svg className={className} viewBox="0 0 20 20" aria-hidden="true">
      <path d="m4 10.5 4 4L16 6" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
