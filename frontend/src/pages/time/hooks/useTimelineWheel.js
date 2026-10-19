import { useEffect, useRef } from "react";

const STEP_INTERVAL_MS = 300;
const WHEEL_IDLE_MS = 160;

export default function useTimelineWheel(root, active, count, onSelect) {
  const gesture = useRef({ navigating: false, lastStepAt: -Infinity, lastWheelAt: -Infinity });

  useEffect(() => {
    const stage = root.current;
    if (!stage) return;

    const onWheel = (event) => {
      if (event.defaultPrevented || !event.cancelable || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
      if (!event.deltaY || Math.abs(event.deltaX) > Math.abs(event.deltaY)) return;
      if (event.target.closest?.("input, textarea, select, [contenteditable]")) return;

      const now = performance.now();
      const state = gesture.current;
      // 한 번 굴린 휠의 연속 입력과 트랙패드 관성으로 여러 시점이 넘어가지 않게 함.
      const continuing = state.navigating && (
        now - state.lastStepAt < STEP_INTERVAL_MS || now - state.lastWheelAt < WHEEL_IDLE_MS
      );
      state.lastWheelAt = now;
      if (continuing) {
        event.preventDefault();
        return;
      }
      state.navigating = false;

      const next = active + Math.sign(event.deltaY);
      // 처음에서 위로, 마지막에서 아래로는 일반 페이지 스크롤로 이어짐.
      if (next < 0 || next >= count) return;

      event.preventDefault();
      state.navigating = true;
      state.lastStepAt = now;
      onSelect(next);
    };

    stage.addEventListener("wheel", onWheel, { passive: false });
    return () => stage.removeEventListener("wheel", onWheel);
  }, [root, active, count, onSelect]);
}
