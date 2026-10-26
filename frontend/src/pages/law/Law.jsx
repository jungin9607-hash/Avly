import { useLocation } from "react-router-dom";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import useNavigationBackdrop from "../common/hooks/useNavigationBackdrop";
import PageHeader from "./components/PageHeader";
import CaseList, { GuideCard } from "./components/CaseList";
import SummaryAside, { SummaryCard } from "./components/SummaryAside";
import StickyCompareBar from "./components/StickyCompareBar";
import CompareModal from "./components/CompareModal";
import AnalysisGate from "../common/components/AnalysisGate";
import { myAccidentPoints, toCaseCards } from "../../api/adapters";
import { EMPTY, SECTION, SUMMARY, GUIDE, STICKY_BAR } from "./lawContent";
import "./Law.css";

// 유사 판례 화면. 서버가 이 사고 유형에 연결해 준 판례와 규칙 기반 비교를 보여 준다.
export default function Law({ analysisId }) {
  return (
    <AnalysisGate analysisId={analysisId} active="유사 판례">
      {({ analysis }) => <LawView result={analysis.result} />}
    </AnalysisGate>
  );
}

export function LawView({ result }) {
  const cases = useMemo(() => toCaseCards(result.related_cases), [result]);
  const myAccident = useMemo(() => ({ label: "내 사고", points: myAccidentPoints(result) }), [result]);
  const pageRef = useRef(null);
  useNavigationBackdrop(pageRef, ".law-band");
  // 처음 들어오면 선택된 판례 없음 → 카드를 눌러야 "비슷한 점" 박스가 나타남
  const [selectedId, setSelectedId] = useState(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const selectedCase = cases.find((item) => item.id === selectedId) ?? null;
  const closeCompare = useCallback(() => setCompareOpen(false), []);

  // 분석 결과 화면 안(저장·공유 아래)에 들어간다. 주소 끝이 #similar-cases(타임라인의 "유사 판례 바로가기")면 이 구간으로 내려온다.
  const { hash } = useLocation();
  useEffect(() => {
    if (hash === "#similar-cases") pageRef.current?.scrollIntoView();
  }, [hash]);
  // 같은 카드를 다시 누르면 선택 해제 → "비슷한 점" 박스도 사라짐
  const toggleCase = (id) => setSelectedId((current) => (current === id ? null : id));
  const openCompare = () => setCompareOpen(true);
  const listRef = useRef(null);
  const summary = selectedCase && <SummaryCard content={SUMMARY} caseItem={selectedCase} />;

  return (
    <div className="law-page" id="similar-cases" ref={pageRef}>
      {/* 메뉴 바는 intro와 같은 기본 스타일 (색은 Law.css에서 intro 밤하늘 위 모습과 같게) */}

      {/* 위에서 아래로 배경색이 자연스럽게 이어지는 두 구간: 메뉴 바와 이어지는 진한 남색 → 비교 버튼 네이비 */}
      <main className="law-main">
        <section className="law-band law-band-warm">
          <div className="law-band-inner">
            <PageHeader section={SECTION} myAccident={myAccident} />
            <div className="law-grid">
              {/* 왼쪽: 판례 카드 3개 + 바로 아래 활용 가이드 */}
              <div className="law-case-column">
                {cases.length === 0 && (
                  <section className="law-empty">
                    <h3>{EMPTY.title}</h3>
                    <p>{EMPTY.text}</p>
                  </section>
                )}
                <CaseList
                  ref={listRef}
                  cases={cases}
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

      </main>

      {/* law-main 밖에 두어 메뉴 바보다 위에 뜨게 */}
      {compareOpen && selectedCase && <CompareModal caseItem={selectedCase} onClose={closeCompare} />}
    </div>
  );
}
