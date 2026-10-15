export function getTimelinePosition(moments, time) {
  const start = moments[0].time;
  const end = moments[moments.length - 1].time;
  return end === start ? 0 : Math.max(0, Math.min(100, ((time - start) / (end - start)) * 100));
}

export function getTimelineColor(position) {
  return `color-mix(in srgb, var(--signal) ${100 - position}%, rgb(var(--tl-impact-dot-rgb)))`;
}
