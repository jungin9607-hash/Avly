import { useEffect, useRef, useState } from "react";
import TopNav from "../../components/common/TopNav";
import ReportNotice from "./ReportNotice";
import AdjustmentSteps from "./AdjustmentSteps";
import ReportHeader from "./ReportHeader";
import "./Report.css";

// 과실 조정 요인: 최종 비율과 함께 한눈에 표시
const STEPS = [
  {
    title: "차선 변경 사고의 기본 기준 (30:70)",
    tag: "기본율 적용",
    ratio: [30, 70],
    body: "같은 방향으로 달리던 차량이 차선을 바꾸다가 발생한 사고이므로 사고 유형의 기본 기준에 따라 내 과실 30%, 상대 과실 70%에서 시작",
  },
  {
    title: "상대 차량이 깜빡이 미점등",
    tag: "-5%p 감산",
    ratio: [25, 75],
    body: "영상 분석 결과 상대 차량이 깜빡이를 미점등인 상태에서 차선을 바꾸는 모습이 확인되어 상대 차량의 진입을 미리 예상하기 어려워 내 과실을 5%p 감소",
  },
  {
    title: "상대 차량의 급격한 진입으로 회피가 어려운 상황",
    tag: "-5%p 추가 감산",
    ratio: [20, 80],
    body: "상대 차량이 가까운 거리에서 갑자기 진입하여 충돌을 피할 시간이 부족하였기때문에 내 과실을 추가로 5%p 감소",
  },
];

const FRAMES = ["00:23.8", "00:24.1", "00:24.5"];

export default function Report() {
  const [toast, setToast] = useState("");
  const reportRef = useRef(null);

  useEffect(() => {
    const report = reportRef.current;
    const updateWidth = () => report.style.setProperty("--ar-viewport-width", `${report.clientWidth}px`);
    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    observer.observe(report);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(""), 2200);
    return () => clearTimeout(id);
  }, [toast]);

  const share = async () => {
    const data = { title: "에블리 과실 분석 결과 · AV-24901", url: window.location.href };
    try {
      if (navigator.share) {
        await navigator.share(data);
      } else {
        await navigator.clipboard.writeText(data.url);
        setToast("결과 링크를 복사했어요");
      }
    } catch {
      // 사용자가 공유 창을 닫은 경우 등은 조용히 무시
    }
  };

  return (
    <div className="ar" ref={reportRef}>
      <TopNav active="분석 결과" theme="light" />

      <main className="ar-main">
        {/* 최종 과실 비율과 전체 조정 요인을 함께 표시 */}
        <section className="ar-section ar-report-page ar-result-page">
          <ReportHeader reportCode="AV-24901" accidentType="차선 변경 중 접촉 사고" />
          <AdjustmentSteps steps={STEPS} />
        </section>

        {/* 핵심 증거 */}
        <section className="ar-section ar-report-page ar-evidence-page">
          <header className="ar-sec-head">
            <h2>과실 산정 핵심 증거</h2>
          </header>

          <div className="ar-evidence">
            <Reveal className="ar-ev ar-ev-wide">
              {() => (
                <>
                  <EvidenceHead title="상대 차량 방향지시등 미점등" tag="99.8% 미동작" />
                  <p>
                    진입 전 3개 연속 프레임(초당 30fps) 픽셀 조도 추적 결과 방향지시등 비활성 상태가 정밀
                    입증되었습니다.
                  </p>
                  <div className="ar-frames">
                    {FRAMES.map((t, i) => (
                      <figure key={t} className="ar-frame" style={{ "--i": i }}>
                        <CarRear />
                        <span className="ar-frame-scan" aria-hidden="true" />
                        <span className="ar-frame-box" aria-hidden="true" />
                        <figcaption>{t}</figcaption>
                      </figure>
                    ))}
                  </div>
                </>
              )}
            </Reveal>

            <Reveal className="ar-ev" delay={80}>
              {() => (
                <>
                  <EvidenceHead title="규정속도 준수 및 직진 차선 유지" tag="46km/h 준수" />
                  <p>
                    GPS 센서 데이터 및 도로 차선 간격 분석 결과, 내 차량은 제한속도(50km/h) 이하로 2차로
                    중심선 정중앙을 유지하고 있었습니다.
                  </p>
                  <p className="ar-ev-foot">
                    <IconTarget />
                    차로 이탈률 0.04m 이내 (안정적 직진 주행 완료)
                  </p>
                </>
              )}
            </Reveal>

            <Reveal className="ar-ev" delay={160}>
              {() => (
                <>
                  <EvidenceHead title="무리한 급진입 및 제동 불가항력" tag="TTC 0.72초" warn />
                  <p>
                    인간 운전자의 평균 제동 인지 반응 시간(0.7초~1.0초)을 밑도는 시점에 급격히 유입되어 충돌
                    회피 기회가 물리적으로 결여되었습니다.
                  </p>
                  <p className="ar-ev-foot">
                    <IconGavel />
                    대법원 2018다293282 &apos;회피 불능 신뢰의 원칙&apos; 부합
                  </p>
                </>
              )}
            </Reveal>
          </div>

          <div className="ar-actions">
            <button type="button" className="ar-btn ar-btn-solid" onClick={() => window.print()}>
              <IconDownload />
              PDF 다운로드
            </button>
            <button type="button" className="ar-btn ar-btn-line" onClick={share}>
              <IconShare />
              공유하기
            </button>
          </div>
          <ReportNotice />
        </section>

      </main>

      <p className={toast ? "ar-toast is-on" : "ar-toast"} role="status">
        {toast}
      </p>
    </div>
  );
}

/* ---------- 작은 부품 ---------- */

function Reveal({ className, delay = 0, children }) {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setInView(true);
          io.disconnect();
        }
      },
      { threshold: 0.25 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <article
      ref={ref}
      className={`${className} ar-reveal${inView ? " is-in" : ""}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children(inView)}
    </article>
  );
}

function EvidenceHead({ title, tag, warn = false }) {
  return (
    <div className="ar-ev-head">
      <h3>
        <IconCheck />
        {title}
      </h3>
      <span className={warn ? "ar-ev-tag warn" : "ar-ev-tag"}>{tag}</span>
    </div>
  );
}

// 블랙박스 프레임 자리: 앞차 뒷모습 (왼쪽 방향지시등 자리를 표시)
function CarRear() {
  return (
    <svg className="ar-car" viewBox="0 0 160 90" aria-hidden="true">
      <rect x="0" y="62" width="160" height="28" fill="#2a2a33" />
      <path d="M0 76 H160" stroke="#55555f" strokeWidth="1" strokeDasharray="10 8" />
      <path d="M44 30 Q48 16 62 14 H98 Q112 16 116 30 Z" fill="#3a3d48" />
      <path d="M52 28 Q55 19 64 18 H96 Q105 19 108 28 Z" fill="#1b1d24" />
      <rect x="36" y="30" width="88" height="30" rx="5" fill="#5b5f6c" />
      <rect x="40" y="36" width="16" height="7" rx="1.5" fill="#6b2a2a" />
      <rect x="104" y="36" width="16" height="7" rx="1.5" fill="#6b2a2a" />
      <rect x="68" y="46" width="24" height="7" rx="1" fill="#d9d9de" />
      <rect x="40" y="60" width="12" height="7" rx="2" fill="#16161b" />
      <rect x="108" y="60" width="12" height="7" rx="2" fill="#16161b" />
    </svg>
  );
}

/* ---------- 아이콘 ---------- */
const Svg = ({ children, size = 18 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.9"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);
const IconCheck = () => (
  <Svg size={18}>
    <circle cx="12" cy="12" r="9" />
    <path d="m8.5 12 2.5 2.5 4.5-5" />
  </Svg>
);
const IconTarget = () => (
  <Svg size={15}>
    <circle cx="12" cy="12" r="8" />
    <circle cx="12" cy="12" r="3" />
    <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
  </Svg>
);
const IconGavel = () => (
  <Svg size={15}>
    <path d="m14 4 6 6M11 7l6 6M12.5 5.5l-6 6M18.5 11.5l-6 6M9 14l-6 6M3 21h9" />
  </Svg>
);
const IconDownload = () => (
  <Svg size={17}>
    <path d="M12 4v11M7 10l5 5 5-5M5 20h14" />
  </Svg>
);
const IconShare = () => (
  <Svg size={17}>
    <circle cx="18" cy="5" r="2.5" />
    <circle cx="6" cy="12" r="2.5" />
    <circle cx="18" cy="19" r="2.5" />
    <path d="m8.2 10.8 7.6-4.4M8.2 13.2l7.6 4.4" />
  </Svg>
);
