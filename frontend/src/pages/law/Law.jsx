import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import TopNav from "../../components/common/TopNav";
import LegalNotice from "../../components/common/LegalNotice";
import PageHeader from "./components/PageHeader";
import CaseList, { GuideCard } from "./components/CaseList";
import SummaryAside, { SummaryCard } from "./components/SummaryAside";
import StickyCompareBar from "./components/StickyCompareBar";
import CompareModal from "./components/CompareModal";
import { CASES } from "./lawCases";
import { SECTION, SUMMARY, GUIDE, MY_ACCIDENT, STICKY_BAR } from "./lawContent";
import "./Law.css";

export default function Law() {
  // 처음 들어오면 선택된 판례 없음 → 카드를 눌러야 "비슷한 점" 박스가 나타남
  const [selectedId, setSelectedId] = useState(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const selectedCase = CASES.find((item) => item.id === selectedId) ?? null;
  const closeCompare = useCallback(() => setCompareOpen(false), []);

  // 다른 페이지에 갔다 와도 이전 스크롤 위치가 남지 않고 항상 맨 위(처음 화면)에서 시작
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);
  // 같은 카드를 다시 누르면 선택 해제 → "비슷한 점" 박스도 사라짐
  const toggleCase = (id) => setSelectedId((current) => (current === id ? null : id));
  const openCompare = () => setCompareOpen(true);
  const listRef = useRef(null);
  const summary = selectedCase && <SummaryCard content={SUMMARY} caseItem={selectedCase} />;

  return (
    <div className="law-page">
      {/* 메뉴 바는 intro와 같은 기본 스타일 (색은 Law.css에서 intro 밤하늘 위 모습과 같게) */}
      <TopNav active="유사 판례" />

      {/* 위에서 아래로 배경색이 자연스럽게 이어지는 두 구간: 메뉴 바와 이어지는 진한 남색 → 비교 버튼 네이비 */}
      <main className="law-main">
        <section className="law-band law-band-warm">
          {/* 배경 워터마크: 아주 옅은 "Avly" 글자 */}
          <span className="law-wordmark" aria-hidden="true">Avly</span>
          <div className="law-band-inner">
            <PageHeader section={SECTION} myAccident={MY_ACCIDENT} />
            <div className="law-grid">
              {/* 왼쪽: 판례 카드 3개 + 바로 아래 활용 가이드 */}
              <div className="law-case-column">
                <CaseList
                  ref={listRef}
                  cases={CASES}
                  selectedId={selectedId}
                  onToggle={toggleCase}
                  selectedExtra={summary}
                />
                <GuideCard content={GUIDE} />
              </div>
              {/* 오른쪽: 선택한 판례 카드 옆으로 따라 내려가는 "비슷한 점" 박스 */}
              <SummaryAside listRef={listRef} selectedId={selectedId}>
                {summary}
              </SummaryAside>
            </div>

            {/* "내 사고와 비교하기"는 이 바 하나로: 평소엔 판례 목록 바로 아래,
                상세 보기로 페이지가 길어지면 화면 아래에 붙어 따라옴 (법적 고지보다 위) */}
            <StickyCompareBar
              content={STICKY_BAR}
              caseItem={selectedCase}
              onOpen={openCompare}
            />
          </div>
        </section>

        <section className="law-band law-band-sand">
          <div className="law-band-inner">
            <LegalNotice />
            <div className="law-back-link">
              <Link to="/analysis-test">분석 결과로 돌아가기</Link>
            </div>
          </div>
        </section>
      </main>

      {/* law-main 밖에 두어 메뉴 바보다 위에 뜨게 */}
      {compareOpen && selectedCase && <CompareModal caseItem={selectedCase} onClose={closeCompare} />}
    </div>
  );
}
