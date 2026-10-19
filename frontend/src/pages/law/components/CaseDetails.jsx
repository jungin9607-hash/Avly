// "상세 보기"를 펼치면 나오는 판례 설명: 요약 → 이 판례를 그대로 적용하기 어려운 점 → 출처
// 판례 요약과 출처만 가지고 있다. 사건 경위나 법원 판단 요지처럼 없는 내용은 보여 주지 않는다.
// open: 펼침 여부 (닫혀 있어도 그려 두고 높이만 0으로 접어, 펼칠 때 부드럽게 내려옴)
export default function CaseDetails({ item, open }) {
  return (
    <div className={`law-details-collapse${open ? " is-open" : ""}`} inert={!open}>
      <div className="law-details-clip">
        {/* 읽는 영역이라 눌러도 카드 선택(on/off)이 바뀌지 않게 */}
        <div className="law-case-details" onClick={(e) => e.stopPropagation()}>
          <p className="law-details-overview">{item.summary}</p>

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
