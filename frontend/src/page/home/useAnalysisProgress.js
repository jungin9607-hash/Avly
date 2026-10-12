import { useCallback, useEffect, useRef, useState } from "react";
import { STAGE, isAnalyzingStage } from "./constants";

const PROGRESS_STEPS = [50, 85, 100];

// 분석 진행률 시뮬레이션. 끝나면 start()에서 지정한 다음 단계로 이동한다.
export function useAnalysisProgress(stage, setStage) {
  const [progress, setProgress] = useState(0);
  const intervalRef = useRef(null);
  const timeoutRef = useRef(null);
  const nextStageRef = useRef(STAGE.QUESTIONNAIRE);

  const stop = useCallback(() => {
    clearInterval(intervalRef.current);
    clearTimeout(timeoutRef.current);
  }, []);

  useEffect(() => {
    if (!isAnalyzingStage(stage)) return;

    stop();

    let index = 0;

    intervalRef.current = setInterval(() => {
      setProgress(PROGRESS_STEPS[index]);
      index += 1;

      if (index >= PROGRESS_STEPS.length) {
        clearInterval(intervalRef.current);
        timeoutRef.current = setTimeout(() => setStage(nextStageRef.current), 900);
      }
    }, 1000);

    return stop;
  }, [stage, setStage, stop]);

  const start = (nextStage = STAGE.QUESTIONNAIRE, reanalysis = false) => {
    setProgress(15);
    nextStageRef.current = nextStage;
    setStage(reanalysis ? STAGE.REANALYZING : STAGE.ANALYZING);
  };

  const fastForward = () => {
    stop();
    setProgress(100);
    timeoutRef.current = setTimeout(() => setStage(nextStageRef.current), 300);
  };

  return { progress, start, fastForward, stop };
}
