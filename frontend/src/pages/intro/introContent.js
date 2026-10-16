// 인트로 화면의 문구·링크 (화면 구조는 components/ 에서 이 데이터를 받아 그림)

export const HERO = {
  label: "AI 블랙박스 과실 분석",
  titleLines: ["사고의 순간부터,", "과실비율의 근거까지"],
  scrollHint: "스크롤 또는 스페이스바",
  action: { label: "블랙박스 영상 분석하러 가기", to: "/upload-test" },
};

// visual: components/visuals 의 어떤 그림을 쓸지
// desc: 카드 설명 조각 배열, { em: "..." }는 핵심 단어 표시, { br: true }는 그 자리에서 줄바꿈
//   (그 외 줄바꿈은 박스 폭에 맞춰 자동)
export const FEATURES = {
  title: "에블리가 하는 일",
  cards: [
    {
      id: "video",
      title: "블랙박스 영상 분석",
      visual: "cam",
      desc: [
        "블랙박스 영상의 ",
        { em: "사고 유형" },
        "과 ",
        { em: "충돌 시점" },
        "을 파악하고 충돌 전후 주요 장면을 ",
        { em: "타임라인" },
        "으로 보여줍니다.",
      ],
    },
    {
      id: "ratio",
      title: "예상 과실비율과 과실 인정 기준",
      visual: "ratio",
      desc: [
        "사고 유형에 해당하는 ",
        { em: "예상 과실비율" },
        "과",
        { br: true },
        "과실 인정 기준에 따른 ",
        { em: "가감 요소" },
        "를 보여줍니다.",
      ],
    },
    {
      id: "precedent",
      title: "비슷한 사고의 판례",
      visual: "doc",
      desc: [
        "내 사고와 ",
        { em: "비슷한 판례" },
        "를 찾아,",
        { br: true },
        { em: "공통점과 차이점" },
        "을 쉬운 말로 비교해 드립니다.",
      ],
    },
  ],
};

export const CTA = {
  buttons: [{ label: "블랙박스 영상 분석하러 가기", to: "/upload-test", variant: "accent", arrow: true }],
};
