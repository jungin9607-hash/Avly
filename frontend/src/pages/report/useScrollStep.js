import { useEffect, useRef, useState } from "react";

// 넓은 화면(Report.css의 넓은 화면 조건과 같음)에서 결과 화면이 한 화면에 다 들어가면
// 결과 화면을 고정해 두고 스크롤 거리로 단계를 넘김
const WIDE_QUERY = "(min-width: 901px)";
const NAV_HEIGHT = 64;
// 단계별로 기본 길이(1)보다 더 스크롤해야 넘어가는 만큼: 1 → 2는 50%, 2 → 3은 30% 더
// (합계 0.8 = Report.css의 track 높이 "+ 0.8"과 같은 값)
const STEP_EXTRA = [0.5, 0.3];
const EXTRA_TOTAL = STEP_EXTRA.reduce((sum, extra) => sum + extra, 0);

// 구간 길이 단위(u)로 단계 계산: i번째 구간 길이 = 1 + STEP_EXTRA[i] (없으면 1)
const stepFromUnits = (u, count) => {
  let end = 0;
  for (let i = 0; i < count - 1; i += 1) {
    end += 1 + (STEP_EXTRA[i] ?? 0);
    if (u < end) return i;
  }
  return count - 1;
};

const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// 스크롤 위치에 따라 지금 보여 줄 과실 조정 단계(0 = 기본 기준 ~ count - 1 = 최종)와
// 결과 화면을 고정했는지(pinned)를 돌려줌
export function useScrollStep(sectionRef, count) {
  const [step, setStep] = useState(0);
  const [pinned, setPinned] = useState(false);

  useEffect(() => {
    const section = sectionRef.current;
    const pin = section.querySelector(".ar-result-pin");
    const media = window.matchMedia(WIDE_QUERY);
    let frame = 0;
    // 고정 여부와 단계 간격은 화면 크기가 바뀔 때만 다시 정함
    // ("법적 근거 자세히 보기"로 내용이 길어져도 단계·고정이 바뀌어 비율 박스가 움직이지 않도록)
    let canPin = false;
    let gap = 1;

    const layout = () => {
      // 내용이 화면보다 길면 고정하지 않음 (고정하면 아랫부분이 잘려 보이지 않으므로)
      canPin = media.matches && pin.scrollHeight <= window.innerHeight - NAV_HEIGHT + 1;
      setPinned(canPin);
      // 넓은 화면(고정하지 않을 때)의 단계 간격 = 2번 → 3번 카드 사이 거리
      const cards = section.querySelectorAll(".ar-factor-card");
      if (cards.length > 2) gap = Math.max(cards[2].offsetTop - cards[1].offsetTop, 1);
    };

    const measure = () => {
      frame = 0;
      let next = 0;
      if (canPin) {
        // 고정 구간: 섹션이 메뉴 바 아래에 닿은 뒤 스크롤한 거리 ÷ 여분 스크롤 길이
        const track = section.querySelector(".ar-result-track");
        const scrolled = NAV_HEIGHT - section.getBoundingClientRect().top;
        const progress = Math.min(Math.max(scrolled / Math.max(track.offsetHeight, 1), 0), 1);
        // 구간을 나눠 각 구간을 끝까지 내려야 다음 단계 (첫 구간만 조금 더 길고, 마지막 구간은 최종 유지)
        next = stepFromUnits(progress * (count + EXTRA_TOTAL), count);
      } else {
        const cards = section.querySelectorAll(".ar-factor-card");
        if (media.matches && cards.length > 2) {
          // 넓은 화면(고정하지 않을 때): 2번 → 3번 카드 사이 거리(= 2 → 3에 드는 스크롤 길이)만큼
          // 맨 위에서부터 내릴 때마다 다음 단계 (1 → 2, 2 → 3은 그보다 조금 더 길게)
          const scrolledSoFar = section.closest(".ar").scrollTop;
          next = stepFromUnits(scrolledSoFar / gap, count);
        } else {
          // 좁은 화면: 조정 요인 카드가 화면 40% 높이 선까지 올라와야 다음 단계
          const line = window.innerHeight * 0.4;
          cards.forEach((card, i) => {
            if (card.getBoundingClientRect().top < line) next = i;
          });
        }
      }
      setStep(next);
    };
    // 단계는 사용자가 스크롤할 때만 다시 계산
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(measure);
    };
    const relayout = () => {
      layout();
      schedule();
    };
    // 인쇄할 때는 최종 결과로
    const showFinal = () => setStep(count - 1);

    layout();
    measure();
    // 글꼴이 늦게 들어오면 높이가 달라지므로 한 번 더 잼
    let alive = true;
    document.fonts?.ready.then(() => alive && relayout());
    // capture: 넓은 화면은 .ar 자체가, 좁은 화면은 창이 스크롤되므로 둘 다 받음
    window.addEventListener("scroll", schedule, { capture: true, passive: true });
    window.addEventListener("resize", relayout);
    window.addEventListener("beforeprint", showFinal);
    media.addEventListener("change", relayout);
    return () => {
      alive = false;
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule, { capture: true });
      window.removeEventListener("resize", relayout);
      window.removeEventListener("beforeprint", showFinal);
      media.removeEventListener("change", relayout);
    };
  }, [sectionRef, count]);

  return { step, pinned };
}

// 숫자가 이전 값에서 새 값으로 부드럽게 올라가거나 내려감
export function useAnimatedNumber(target, duration = 600) {
  const [value, setValue] = useState(target);
  const shown = useRef(target); // 지금 화면에 보이는 값 (중간에 바뀌어도 거기서부터 이어서)

  useEffect(() => {
    const set = (next) => {
      shown.current = next;
      setValue(next);
    };
    if (reducedMotion()) {
      set(target);
      return undefined;
    }
    const from = shown.current;
    let frame = 0;
    let start = 0;
    const tick = (now) => {
      if (!start) start = now;
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - (1 - t) ** 3;
      set(Math.round(from + (target - from) * eased));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);

  return value;
}
