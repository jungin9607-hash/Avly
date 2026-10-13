import { useState } from "react";
import { Link } from "react-router-dom";
import TopNav from "../../components/common/TopNav";
import LegalNotice from "../../components/common/LegalNotice";
import purpleWeave from "../../assets/purple-weave.jpg";
import "./Law.css";

const CASES = [
  {
    id: "seoul",
    court: "서울중앙지방법원",
    date: "2022가단5188**",
    category: "손해배상(자) · 선행차량",
    similarity: "98.4%",
    summary: "차로 변경 차량의 방향지시등 미점등 및 안전거리 미확보 추돌",
    ratio: "20 : 80",
    details:
      "직진 차량이 차로를 유지하며 주행하던 중, 상대 차량이 방향지시등을 켜지 않은 채 근접 거리에서 진로를 변경해 발생한 사고입니다. 법원은 진로 변경 차량의 주의의무 위반을 주요 과실 요소로 판단했습니다.",
    factors: ["방향지시등 미점등", "차로 변경 중 접촉", "직진 차량 우선 주행"],
  },
  {
    id: "suwon",
    court: "수원지방법원",
    date: "2021나2043***",
    category: "구상금 · 승용차 대 승용차",
    similarity: "96.2%",
    summary: "주행 중 상대 차량의 급진입으로 발생한 차선 변경 사고",
    ratio: "15 : 85",
    details:
      "주행 차로에서 정상 속도로 진행하던 차량 앞으로 상대 차량이 급하게 진입했습니다. 진입 시점의 거리와 상대 차량의 방향지시등 작동 여부가 과실 비율을 정하는 주요 사정으로 고려되었습니다.",
    factors: ["급격한 차로 진입", "제동 가능 시간 부족", "차량 간 거리"],
  },
  {
    id: "daegu",
    court: "대구지방법원",
    date: "2023나1109***",
    category: "손해배상(자) · 일반도로 직진",
    similarity: "94.7%",
    summary: "차선 변경 차량의 급진입 및 방향지시등 미점등",
    ratio: "20 : 80",
    details:
      "일반도로에서 직진하던 차량과 차로를 변경하던 차량이 충돌한 사건입니다. 블랙박스 영상에서 방향지시등 미점등과 짧은 차간 거리가 확인되어 차로 변경 차량의 책임이 더 크게 인정되었습니다.",
    factors: ["방향지시등 미점등", "차간 거리 부족", "블랙박스 영상 확인"],
  },
];

function RoadEvidence() {
  return (
    <svg
      className="law-road"
      viewBox="0 0 480 180"
      role="img"
      aria-label="차량의 차선 변경 상황을 표시한 사고 영상 분석 예시"
    >
      <defs>
        <linearGradient id="law-road-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#dbe8f4" />
          <stop offset="1" stopColor="#f4f7fb" />
        </linearGradient>
        <linearGradient id="law-road-surface" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#414958" />
          <stop offset="1" stopColor="#252b37" />
        </linearGradient>
      </defs>
      <rect width="480" height="180" fill="url(#law-road-sky)" />
      <path d="M0 72h480v108H0z" fill="url(#law-road-surface)" />
      <path d="m0 180 154-108h172L480 180" fill="#343b49" />
      <path d="m0 180 170-108M480 180 310 72" stroke="#eef3f8" strokeWidth="4" />
      <path d="m236 180 2-25m2-19 2-22m2-18 2-24" stroke="#fff" strokeWidth="4" strokeDasharray="13 12" />
      <path d="M87 154c87-17 139-34 207-66" fill="none" stroke="#1c9b72" strokeWidth="4" strokeDasharray="7 5" />
      <path d="M87 154c87-17 139-34 207-66" fill="none" stroke="#fff" strokeWidth="1.5" />
      <g transform="translate(286 84) rotate(-12)">
        <rect x="-27" y="-18" width="54" height="35" rx="8" fill="#e8edf4" stroke="#243044" strokeWidth="3" />
        <path d="m-17-14 5-9h24l6 9" fill="#8ca0b9" stroke="#243044" strokeWidth="2" />
        <circle cx="-17" cy="13" r="5" fill="#171d28" />
        <circle cx="17" cy="13" r="5" fill="#171d28" />
      </g>
      <g transform="translate(153 135)">
        <rect x="-31" y="-19" width="62" height="39" rx="9" fill="#2863cb" stroke="#fff" strokeWidth="3" />
        <path d="m-19-15 6-10h26l7 10" fill="#90b3f2" stroke="#fff" strokeWidth="2" />
        <circle cx="-19" cy="15" r="5" fill="#171d28" />
        <circle cx="19" cy="15" r="5" fill="#171d28" />
      </g>
      <rect x="310" y="21" width="142" height="28" rx="5" fill="#fff" fillOpacity=".94" />
      <circle cx="325" cy="35" r="4" fill="#20a879" />
      <text x="337" y="40" fill="#253248" fontSize="13" fontWeight="700">차선 변경 경로 분석</text>
      <rect x="15" y="15" width="82" height="25" rx="4" fill="#172235" fillOpacity=".78" />
      <circle cx="28" cy="27" r="4" fill="#e65353" />
      <text x="38" y="31" fill="#fff" fontSize="11" fontWeight="700">AI FRAME</text>
    </svg>
  );
}

export default function Law() {
  const [selectedId, setSelectedId] = useState(CASES[2].id);
  const [detailsId, setDetailsId] = useState(null);
  const [compared, setCompared] = useState(false);
  const selectedCase = CASES.find((item) => item.id === selectedId);
  const [mineRatio, otherRatio] = selectedCase.ratio.split(":").map(Number);

  const selectCase = (id) => {
    setSelectedId(id);
    setCompared(false);
  };

  return (
    <div className="law-page">
      <TopNav active="유사 판례" theme="dark" />

      <header className="law-hero" style={{ "--hero-photo": `url(${purpleWeave})` }}>
        <div className="law-hero-inner">
          <div className="law-heading">
            <div>
              <p className="law-eyebrow">AI CASE MATCHING</p>
              <h1>유사 판례 분석</h1>
              <p className="law-hero-description">
                내 사고와 유사한 판례를 비교해 과실 판단의 참고 근거를 확인하세요.
              </p>
            </div>
            <span className="law-result-count">
              <i /> 가장 유사한 판례 3건
            </span>
          </div>
        </div>
      </header>

      <main className="law-main">
        <div className="law-grid">
          <section className="law-case-list" aria-label="유사 판례 목록">
            {CASES.map((item, index) => {
              const isSelected = item.id === selectedId;
              const isExpanded = item.id === detailsId;
              return (
                <article
                  key={item.id}
                  className={`law-case${isSelected ? " is-selected" : ""}`}
                >
                  <div className="law-case-top">
                    <label className="law-case-select">
                      <input
                        type="radio"
                        name="similar-case"
                        value={item.id}
                        checked={isSelected}
                        onChange={() => selectCase(item.id)}
                      />
                      <span className="law-case-number">{index + 1}</span>
                      <span className="law-court">
                        <strong>{item.court}</strong>
                        <small>{item.date} 판결</small>
                        <em>{item.category}</em>
                      </span>
                    </label>
                    <span className="law-similarity">
                      <span aria-hidden="true">⌕</span> 유사도 {item.similarity}
                    </span>
                  </div>

                  <p className="law-case-summary">
                    <span aria-hidden="true">↗</span>
                    <span>사고 상황: {item.summary}</span>
                  </p>

                  <div className="law-case-bottom">
                    <span className={isSelected ? "law-selected-label" : ""}>
                      {isSelected ? "선택된 판례" : "선택 가능"}
                    </span>
                    <span>기준 과실 {item.ratio}</span>
                    <button
                      type="button"
                      aria-expanded={isExpanded}
                      onClick={() => setDetailsId(isExpanded ? null : item.id)}
                    >
                      {isExpanded ? "접기" : "상세 보기"}
                      <span aria-hidden="true">{isExpanded ? "−" : "↗"}</span>
                    </button>
                  </div>

                  {isExpanded && (
                    <div className="law-case-details">
                      <p>{item.details}</p>
                      <ul>
                        {item.factors.map((factor) => <li key={factor}>{factor}</li>)}
                      </ul>
                    </div>
                  )}
                </article>
              );
            })}
          </section>

          <aside className="law-analysis">
            <section className="law-summary-card">
              <div className="law-card-heading">
                <h2><span aria-hidden="true">◈</span> AI 판례 유사도 매칭 요약</h2>
                <span>신뢰도 96%</span>
              </div>

              <div className="law-ratio">
                <div className="law-ratio-top">
                  <span>선택된 판례</span>
                  <strong>{mineRatio}:{otherRatio}</strong>
                </div>
                <div
                  className="law-ratio-bar"
                  role="img"
                  aria-label={`내 과실 ${mineRatio}%, 상대 과실 ${otherRatio}%`}
                >
                  <span style={{ width: `${mineRatio}%` }} />
                </div>
                <div className="law-ratio-labels">
                  <span>내 과실 {mineRatio}%</span>
                  <span>상대 과실 {otherRatio}%</span>
                </div>
              </div>

              <ul className="law-reasons">
                <li><span>✓</span><p>진입 직전 방향지시등 미점등과 안전거리 미확보가 확인된 유사 판례를 우선 비교했습니다.</p></li>
                <li><span>✓</span><p>내 차량은 직진 차로에서 정상 주행 중이었으며, 상대 차량의 급격한 진로 변경이 주요 원인으로 판단됩니다.</p></li>
              </ul>

              <figure className="law-evidence">
                <RoadEvidence />
                <figcaption><span>▣</span> 블랙박스 프레임 분석 예시</figcaption>
              </figure>
            </section>

            <section className="law-guide">
              <h2><span aria-hidden="true">ⓘ</span> 판례 활용 가이드</h2>
              <p>
                유사 판례는 사고 상황의 공통점과 차이점을 참고하기 위한 자료입니다.
                실제 과실비율은 도로 환경, 차량 속도와 사고 경위에 따라 달라질 수 있습니다.
              </p>
            </section>
          </aside>
        </div>

        <section className={`law-compare${compared ? " is-compared" : ""}`}>
          {compared ? (
            <>
              <p className="law-compare-kicker">선택한 판례와 내 사고의 공통점</p>
              <h2>{selectedCase.court} 판결과 유사한 요소가 확인됐어요</h2>
              <p className="law-compare-result">
                {selectedCase.factors.join(" · ")} — 기준 과실 {selectedCase.ratio}
              </p>
              <button type="button" className="law-compare-button" onClick={() => setCompared(false)}>
                다른 판례 선택하기
              </button>
            </>
          ) : (
            <>
              <h2>선택한 판례와 내 사고 비교하기</h2>
              <p>{selectedCase.court} · {selectedCase.date} 판결이 선택되어 있어요</p>
              <button type="button" className="law-compare-button" onClick={() => setCompared(true)}>
                <span aria-hidden="true">⌘</span>
                선택한 판례와 내 사고 비교하기
              </button>
              <small>비교 결과는 사고 상황을 이해하기 위한 참고 정보입니다.</small>
            </>
          )}
        </section>

        <LegalNotice />

        <div className="law-back-link">
          <Link to="/analysis-test">분석 결과로 돌아가기</Link>
        </div>
      </main>
    </div>
  );
}
