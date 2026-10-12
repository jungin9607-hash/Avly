export const precedents = [
  {
    id: 1,
    court: "서울중앙지방법원",
    caseNumber: "2022가단5188*** 판결",
    type: "손해배상(기) · 선고확정",
    similarity: "98.4%",
    ratio: "20:80",
    summary: "방향지시등 미작동 급차선 변경 후행 차량 추돌",
    icon: "emergency_share",
    detail:
      "상대 차량이 방향지시등 없이 2개 차로를 연속으로 급격히 변경 진입하였고, 직선 주행 중이던 청구인은 회피 가능 거리가 현저히 부족했던 사고입니다. 도로교통법 제19조 및 제38조 위반으로 피청구인 책임 80% 인정됨.",
    diff:
      "내 사고 대비 제동 개시 시점이 0.4초 빨라 과실 5%p 감경 요인 유효",
  },
  {
    id: 2,
    court: "수원지방법원",
    caseNumber: "2021나2043*** 판결",
    type: "구상금 · 항소기각 확정",
    similarity: "96.2%",
    ratio: "15:85",
    summary: "직진 차로 정상 주행 중 상대 차량 사선 급진입 및 급감속",
    icon: "merge_type",
    detail:
      "편도 3차로에서 1차로 직진 주행 중 우측 3차로에서 진입한 차량이 2차로를 통과해 1차로로 사선 급진입 후 급감속한 사안. 진입 차량의 후속 차량에 대한 통행방해 금지 의무 위반 중과실 인정.",
    diff:
      "상대 차량 속도 차이가 유사하나 본 사건은 주간, 판례는 야간 주행",
  },
  {
    id: 3,
    court: "대구지방법원",
    caseNumber: "2023나1109*** 판결",
    type: "손해배상(자) · 일부인용 확정",
    similarity: "94.7%",
    ratio: "10:90",
    summary: "백색 실선 차선변경 금지 위반 및 방향지시등 미점등",
    icon: "warning",
    detail:
      "교량 및 터널 진입 전 백색 실선 구간에서 방향지시등 없이 차선을 침범한 상대 차량의 사고. 피해 차량의 회피 불가능성이 시뮬레이션으로 입증됨.",
    diff:
      "사고 지점이 교차로 부근 점선 구간인지 실선 구간인지에 따른 법적 쟁점 차이 존재",
  },
];

export const comparisonPoints = {
  common: [
    {
      title: "방향지시등 미점등 동일",
      content:
        "도로교통법 제38조(차의 신호) 위반 사실이 영상으로 명확히 판독됨.",
    },
    {
      title: "제한속도 준수",
      content:
        "내 차량 제한속도(60km/h 구간 54km/h 주행) 내 정상 직진 중 추돌.",
    },
    {
      title: "가해차량 급진입",
      content:
        "30미터 전방 안전거리 미확보 및 진로변경 금지 상황 연출.",
    },
  ],
  different: [
    {
      title: "충돌 부위",
      content:
        "판례는 전측면 추돌이었으나, 내 사고는 상대 차량 휠 하우스 사선 침범으로 회피 공간 전무.",
    },
    {
      title: "제동 반응 속도",
      content:
        "판례(0.9초) 대비 0.5초 빠른 감속 반응 확인으로 추가 5%p 유리 요인 도출.",
    },
    {
      title: "최종 예측 과실",
      content:
        "판례 기본 20:80보다 유리한 15:85 협상 권고.",
    },
  ],
};

export const analysisImage =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuBcVQu-7YcxxzzlZVb0f_dnGe_NxDfUw_vbHLmeHaZj7926hRCT5AAeMSwTXQeAXKWwnTWzVvrjSi2lqnZxnD7Ljyfx4ts8ktbNZwSvnry2xc_a1ZTPneheAmafhCF81q35knOMNXERY_lYM_Ryt9nRwPM7dJ0Ve7fRdfTIASVmXdfnvmJt8vWGxYoV2z59E8bvMWbXVAKjOywBbTEDKkSIHxYGOghF7MONvvVqoIMHHFaK_4_j4BC_0A";
