import { useEffect, useState } from "react";

// 숫자가 뒤섞이는 간격(ms): 처음엔 빠르게, 끝으로 갈수록 느려지며 멈추는 느낌
const SHUFFLE_DELAYS = [50, 50, 50, 55, 55, 60, 65, 70, 80, 90, 105, 125, 150, 180];

const randomRatio = () => {
  const mine = 5 + Math.floor(Math.random() * 91); // 5 ~ 95
  return [mine, 100 - mine];
};

// 페이지에 들어오면 "산정 중"(숫자가 무작위로 뒤섞임) → "완료"(최종 비율에 멈춤)
// 돌려주는 값: { done, ratio } — ratio는 지금 화면에 보여 줄 [내 과실, 상대 과실]
export default function useCalculating(finalRatio) {
  const reduce = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [done, setDone] = useState(reduce);
  const [ratio, setRatio] = useState(reduce ? finalRatio : randomRatio);

  useEffect(() => {
    if (reduce) return undefined;
    let i = 0;
    let timer = 0;
    const next = () => {
      if (i < SHUFFLE_DELAYS.length) {
        setRatio(randomRatio());
        timer = setTimeout(next, SHUFFLE_DELAYS[i]);
        i += 1;
      } else {
        setRatio(finalRatio);
        setDone(true);
      }
    };
    // 화면이 그려진 뒤 잠깐 있다가 시작
    timer = setTimeout(next, 250);
    return () => clearTimeout(timer);
    // finalRatio는 배열이라 값으로 비교
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reduce, finalRatio[0], finalRatio[1]]);

  return { done, ratio };
}
