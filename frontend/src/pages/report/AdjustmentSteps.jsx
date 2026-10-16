import { useLayoutEffect, useRef, useState } from "react";
import FinalRatio from "./FinalRatio";
import StepRatio from "./StepRatio";
import FactorCard from "./FactorCard";
import SectionHeader from "./SectionHeader";

// 위: 최종 과실 비율(고정) / 아래: 왼쪽 움직이는 작은 비율 박스 + 오른쪽 가감요소 목록
export default function AdjustmentSteps({ steps, header, activeIndex = steps.length - 1 }) {
  const [finalMine, finalOther] = steps[steps.length - 1].ratio;
  const listRef = useRef(null);
  const [offset, setOffset] = useState(0);

  // 지금 단계 카드의 세로 위치를 재서 작은 박스를 그 옆으로 옮김 (화면 크기가 바뀌어도 다시 잼)
  useLayoutEffect(() => {
    const list = listRef.current;
    const update = () => setOffset(list.children[activeIndex]?.offsetTop ?? 0);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(list);
    return () => observer.disconnect();
  }, [activeIndex]);

  const cardState = (index) => {
    if (index < activeIndex) return "done";
    if (index === activeIndex) return "active";
    return "upcoming";
  };

  return (
    <div className="ar-factor-overview">
      <FinalRatio mine={finalMine} other={finalOther} />
      {/* 가감요소 구간: 상자 없이 제목 → 기본 기준 카드 | 조정 요인 카드 */}
      <div className="ar-factor-panel">
        <SectionHeader
          kicker={header?.kicker}
          title={`왜 ${finalMine}:${finalOther}으로 분석됐나요?`}
          desc={header?.desc}
        />
        <div className="ar-factor-steps">
          <StepRatio steps={steps} activeIndex={activeIndex} offset={offset} />
          <ol ref={listRef} className="ar-factor-list" aria-label="과실 조정 요인">
            {steps.map((factor, index) => (
              <FactorCard key={factor.title} factor={factor} index={index} state={cardState(index)} />
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}
