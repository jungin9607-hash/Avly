import { IconDashcam, IconMute, IconStopwatch } from "./icons";

const GUIDES = [
  {
    Icon: IconDashcam,
    title: "전방 블랙박스 영상 권장",
    body: "상대 차량의 진입 각도, 도로 차선(실선·점선), 노면 표시 및 신호등 점등 상태가 뚜렷하게 식별될수록 분석 오차가 더욱 감소합니다.",
  },
  {
    Icon: IconStopwatch,
    title: "사고 전후 15초 내외 구간",
    body: "충돌 시점 기준 최소 10초 전 진입 단계부터 충돌 직후 5초 정지 화면까지 포함되어야 AI가 예측 가능성 및 제동 회피 여부를 정확히 판단합니다.",
  },
  {
    Icon: IconMute,
    title: "음성 녹음 여부 무관",
    body: "에블리 AI 비전 모델은 영상 속 장면(이미지)만 분석하므로 블랙박스 내부 대화나 오디오 스트림은 전송 단계에서 완전 음소거 처리됩니다.",
  },
];

/* 영상 가이드 타일 3개: 왼쪽 아이콘 상자 + 오른쪽 제목 · 설명 */
export default function GuideTiles() {
  return (
    <aside className="uh-guides">
      <h2 className="uh-guides-title">정확한 분석을 위한 영상 가이드</h2>
      <ol className="uh-tiles">
        {GUIDES.map((g) => (
          <li key={g.title} className="uh-tile">
            <div className="uh-tile-icon">
              <g.Icon />
            </div>
            <div>
              <h3>{g.title}</h3>
              <p className="uh-tile-body">{g.body}</p>
            </div>
          </li>
        ))}
      </ol>
    </aside>
  );
}
