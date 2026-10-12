import { useEffect, useRef, useState } from "react";
import TopNav from "./TopNav";
import LegalNotice from "./LegalNotice";
import purpleWeave from "../assets/purple-weave.jpg";
import "./AnalysisResult.css";

// 과실 조정 단계: 스크롤하면 왼쪽 비율 게이지가 단계별로 바뀜
const STEPS = [
  {
    title: "표준 과실 기준 (30:70)",
    tag: "기본율 적용",
    ratio: [30, 70],
    body: "동일 방향 진행 중 진로 변경 사고의 표준 과실 기본도표(제252호)에 따라 피변경 차량 30%, 진로변경 차량 70%를 기준값으로 시작합니다.",
  },
  {
    title: "상대측 신호 미표시 (-5%p)",
    tag: "-5%p 감산",
    ratio: [25, 75],
    body: "진로변경 30m 전 방향지시등을 점등하지 않은 상대 차량의 명백한 도로교통법 제38조 위반이 영상 분초 단위(24.3초)로 확인되었습니다.",
  },
  {
    title: "근접 급진입 및 불가항력 (-5%p)",
    tag: "-5%p 추가 감산",
    ratio: [20, 80],
    body: "안전거리 미확보 상태에서 차간 4.2m로 진입하였으며, 인지반응시간(0.8초) 내 충돌 회피가 물리적으로 불가능했음이 텔레메트리로 검증되었습니다.",
  },
];

const TELEMETRY = [
  { icon: "gauge", label: "충돌 1.5초 전 내 속도", value: 46, decimals: 0, unit: "km/h", note: "제한속도 50km/h 내", tone: "ok" },
  { icon: "timer", label: "충돌여유시간 (TTC)", value: 0.72, decimals: 2, unit: "초", note: "회피 한계 도달", tone: "warn" },
  { icon: "brake", label: "제동 반응 시간", value: 0.31, decimals: 2, unit: "초", note: "즉각 브레이크 작동", tone: "ok" },
];

const FRAMES = ["00:23.8", "00:24.1", "00:24.5"];

export default function AnalysisResult() {
  const [ready, setReady] = useState(false); // 처음 열릴 때 막대가 채워지는 연출
  const [stage, setStage] = useState(0);
  const [toast, setToast] = useState("");
  const stepRefs = useRef([]);

  useEffect(() => {
    window.scrollTo(0, 0);
    const id = requestAnimationFrame(() => setReady(true));
    return () => cancelAnimationFrame(id);
  }, []);

  // 화면 가운데를 지나는 단계가 현재 단계
  useEffect(() => {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) setStage(Number(e.target.dataset.index));
        });
      },
      { rootMargin: "-45% 0px -45% 0px" }
    );
    stepRefs.current.forEach((el) => el && io.observe(el));
    return () => io.disconnect();
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

  const [mine, other] = STEPS[stage].ratio;

  return (
    <div className="ar">
      <TopNav active="분석 결과" theme="dark" />

      {/* 맨 위: 보라 직조 사진 띠 위에 최종 과실 비율 */}
      <section className="ar-hero" style={{ "--hero-photo": `url(${purpleWeave})` }}>
        <div className="ar-wrap">
          <div className="ar-meta">
            <span className="ar-code">
              식별 코드 <b>AV-24901</b>
            </span>
            <span className="ar-type">
              <IconSplit />
              사고 유형: 차선 변경 중 접촉 사고
            </span>
          </div>

          <h1>과실 비율 최종 산정치</h1>

          <div className="ar-score">
            <div className="ar-side ar-mine">
              <span className="ar-who">
                <i />내 과실
              </span>
              <strong>
                <CountTo value={20} />
                <small>%</small>
              </strong>
            </div>
            <div className="ar-side ar-other">
              <span className="ar-who">
                <i />
                상대 과실
              </span>
              <strong>
                <CountTo value={80} />
                <small>%</small>
              </strong>
            </div>
          </div>

          <div className="ar-bar" role="img" aria-label="내 과실 20%, 상대 과실 80%">
            <span className="ar-bar-mine" style={{ width: ready ? "20%" : "0%" }}>
              20%
            </span>
            <span className="ar-bar-other" style={{ width: ready ? "80%" : "0%" }}>
              80%
            </span>
          </div>

          <p className="ar-note">
            <IconTrendDown />
            <span>
              기본 과실(30%) 대비 <b>10%p 감산 인정</b> (내 과실 절감 요건 입증 완료)
            </span>
          </p>
        </div>
      </section>

      <main className="ar-main">
        {/* 왜 20:80인가: 왼쪽 게이지는 고정, 오른쪽 단계를 스크롤 */}
        <section className="ar-section">
          <header className="ar-sec-head">
            <h2>왜 20:80으로 분석됐나요?</h2>
            <span>단계별 과실 조정 요인</span>
          </header>

          <div className="ar-scrolly">
            <aside className="ar-gauge" aria-live="polite">
              <p className="ar-gauge-step">
                STEP <b>{String(stage + 1).padStart(2, "0")}</b> / {String(STEPS.length).padStart(2, "0")}
              </p>
              <p className="ar-gauge-ratio">
                <span className="ar-gauge-mine">
                  <CountTo value={mine} from={30} duration={600} />
                </span>
                <em>:</em>
                <span>
                  <CountTo value={other} from={70} duration={600} />
                </span>
              </p>
              <div className="ar-gauge-bar">
                <span style={{ width: `${mine}%` }} />
              </div>
              <div className="ar-gauge-legend">
                <span>
                  <i className="mine" />내 과실
                </span>
                <span>
                  <i className="other" />
                  상대 과실
                </span>
              </div>
              <p className="ar-gauge-caption">{STEPS[stage].title}</p>
              <ol className="ar-gauge-dots" aria-hidden="true">
                {STEPS.map((s, i) => (
                  <li key={s.title} className={i <= stage ? "on" : ""} />
                ))}
              </ol>
            </aside>

            <ol className="ar-steps">
              {STEPS.map((s, i) => (
                <li
                  key={s.title}
                  ref={(el) => {
                    stepRefs.current[i] = el;
                  }}
                  data-index={i}
                  className={i === stage ? "ar-step is-active" : i < stage ? "ar-step is-done" : "ar-step"}
                >
                  <span className="ar-step-num">{i + 1}</span>
                  <div>
                    <div className="ar-step-head">
                      <h3>{s.title}</h3>
                      <span className="ar-step-tag">{s.tag}</span>
                    </div>
                    <p>{s.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* 주행 데이터 */}
        <section className="ar-telemetry" aria-label="주행 데이터">
          {TELEMETRY.map((t, i) => (
            <Reveal key={t.label} className="ar-stat" delay={i * 90}>
              {(inView) => (
                <>
                  <span className="ar-stat-icon">
                    <StatIcon name={t.icon} />
                  </span>
                  <div>
                    <p className="ar-stat-label">{t.label}</p>
                    <p className="ar-stat-value">
                      <CountTo value={t.value} decimals={t.decimals} run={inView} duration={1100} />
                      <small>{t.unit}</small>
                    </p>
                    <p className={`ar-stat-note ${t.tone}`}>{t.note}</p>
                  </div>
                </>
              )}
            </Reveal>
          ))}
        </section>

        {/* 핵심 증거 */}
        <section className="ar-section">
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
        </section>

        <LegalNotice />
      </main>

      <p className={toast ? "ar-toast is-on" : "ar-toast"} role="status">
        {toast}
      </p>
    </div>
  );
}

/* ---------- 작은 부품 ---------- */

const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// 숫자가 목표값까지 부드럽게 올라가거나 내려감
function CountTo({ value, from = 0, run = true, decimals = 0, duration = 900 }) {
  const [shown, setShown] = useState(from);
  const current = useRef(from);

  useEffect(() => {
    if (!run) return;
    const start = current.current;
    const t0 = performance.now();
    let raf;
    const tick = (now) => {
      const p = reduceMotion() ? 1 : Math.min(1, (now - t0) / duration);
      const v = start + (value - start) * (1 - Math.pow(1 - p, 3));
      current.current = v;
      setShown(v);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, run, duration]);

  return shown.toFixed(decimals);
}

// 화면에 들어오면 아래에서 떠오름 (한 번만)
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
const IconSplit = () => (
  <Svg size={16}>
    <path d="M12 21v-7M12 14 6 4M12 14l6-10M4 6l2-2 2 2M16 6l2-2 2 2" />
  </Svg>
);
const IconTrendDown = () => (
  <Svg size={16}>
    <path d="m3 7 6 6 4-4 8 8" />
    <path d="M15 17h6v-6" />
  </Svg>
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
function StatIcon({ name }) {
  if (name === "gauge")
    return (
      <Svg size={20}>
        <path d="M4 17a8 8 0 1 1 16 0" />
        <path d="m12 17 4-5" />
      </Svg>
    );
  if (name === "timer")
    return (
      <Svg size={20}>
        <circle cx="12" cy="13" r="8" />
        <path d="M12 9v4l2.5 2.5M9 2h6" />
      </Svg>
    );
  return (
    <Svg size={20}>
      <path d="M5 12h6M13 12h6M12 5v14" />
      <circle cx="12" cy="12" r="9" />
    </Svg>
  );
}
