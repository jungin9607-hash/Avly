import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(ScrollTrigger, useGSAP);

// 인트로 스크롤 연출 + 휠·스페이스바 단계 이동
// root: 화면 전체 ref, driveRef: RoadScene의 계속 달리는 트윈
export default function useIntroScroll(root, driveRef) {
  useGSAP(
    () => {
      // 어둠 레이어는 화면 아래 바깥에서 대기
      gsap.set(".si-fade", { yPercent: 100 });

      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (reduce) return;

      const drive = driveRef.current;

      // 스크롤에 따라: 제목이 걷히고 → 가속하며 도로 속으로 들어가고 →
      // 아래에서 어둠이 차올라 기능 소개 배경과 이어짐
      gsap
        .timeline({
          defaults: { ease: "none" },
          scrollTrigger: {
            trigger: ".si-hero",
            start: "top top",
            end: "+=350",
            scrub: 1.2,
            pin: true,
            anticipatePin: 1, // 고정이 시작·끝나는 순간 화면이 튀지 않게
            // 스크롤을 빨리 내리면 부드럽게 따라오는 연출(scrub)이 늦어, 어둠이 다 차오르기 전에
            // 도로 맨 아래(노란 중앙선·가장자리 선)가 줄처럼 남아 보임 → 도로 화면을 벗어나는 순간 즉시 마무리
            onLeave: (self) => self.getTween()?.progress(1),
          },
        })
        .to(".si-hero-text", { opacity: 0, y: -80, ease: "power1.in", duration: 0.45 }, 0)
        .to(".si-hero-link", { autoAlpha: 0, y: -24, duration: 0.45 }, 0)
        .to(".si-scroll-hint", { opacity: 0, duration: 0.2 }, 0)
        .to(".si-sky-glow", { opacity: 0, duration: 0.6 }, 0)
        .to(".si-skyline", { opacity: 0, duration: 0.5 }, 0)
        .to(".si-stars", { y: -60, opacity: 0, duration: 0.7 }, 0)
        .to(".si-road", { scale: 2.4, ease: "sine.in", duration: 1 }, 0)
        // 확대·가속되면 자글자글 깨져 보이는 아스팔트 알갱이와 바다 잔물결은 먼저 흐려 없앰
        .to([".si-asphalt-tex", ".si-sea-waves"], { opacity: 0, ease: "power1.out", duration: 0.35 }, 0)
        .to(drive, { timeScale: 3, ease: "power1.in", duration: 1 }, 0) // 도로 속으로 들어가며 가속
        .to(".si-fade", { yPercent: 0, ease: "power1.inOut", duration: 0.7 }, 0.3)
        // 어둠이 거의 다 차오를 무렵 도로도 서서히 사라져, 틈이 생겨도 선이 비치지 않게
        .to(".si-road", { opacity: 0, ease: "power1.in", duration: 0.25 }, 0.75);

      // 기능 소개: 제목·카드·아래 띠가 스크롤에 맞춰 차례로 떠오름
      gsap.from([".si-features h2", ".si-card", ".si-cta-bar"], {
        opacity: 0,
        y: 60,
        stagger: 0.12,
        ease: "power2.out",
        scrollTrigger: {
          trigger: ".si-features",
          start: "top bottom",
          end: "top 30%",
          scrub: 1,
        },
      });

      // 스페이스바로 첫 화면과 기능 소개를 왕복.
      // 이동 중에도 도로·카드 애니메이션은 스크롤에 맞춰 재생됨.
      // Shift+스페이스바로 처음으로 돌아가는 기존 조작도 유지.
      const features = root.current.querySelector(".si-features");
      const introRoot = root.current;
      const getFeaturesTop = () => Math.min(
        features.getBoundingClientRect().top + window.scrollY,
        Math.max(0, document.documentElement.scrollHeight - window.innerHeight)
      );
      let pending = null; // 이동 중인 목표 지점 (빠르게 연달아 눌러도 한 단계씩 넘어가게)
      const moveTo = (target) => {
        pending = target;
        window.scrollTo({ top: target, behavior: "smooth" });
      };
      // 아래 방향 휠은 기능 소개로, 기능 소개 맨 위의 위 방향 휠은 처음으로 이동.
      // 카드 내용을 읽는 구간에서는 기본 스크롤을 유지. 이동 중 이어지는 휠 입력도
      // 기본 스크롤을 막아 브라우저의 부드러운 이동이 중간에 끊기지 않게 함.
      const onWheel = (e) => {
        if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || e.shiftKey) return;
        if (e.deltaY === 0 || Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
          pending = null;
          return;
        }
        const featuresTop = getFeaturesTop();
        const y = window.scrollY;
        const goingDown = e.deltaY > 0;
        if (goingDown ? y >= featuresTop - 4 : y <= 4 || y > featuresTop + 4) return;
        const target = goingDown ? featuresTop : 0;
        e.preventDefault();
        if (pending !== target) moveTo(target);
      };
      const onKeyDown = (e) => {
        if (e.defaultPrevented || e.code !== "Space" || e.ctrlKey || e.metaKey || e.altKey) return;
        // 버튼·입력칸에서는 스페이스바 원래 동작(누르기, 입력) 유지
        if (e.target.closest?.("button, a, input, textarea, select, [contenteditable]")) return;
        // 키를 누르고 있을 때 자동 반복으로 왕복하거나 기본 스크롤이 발생하지 않게 함.
        e.preventDefault();
        if (e.repeat) return;
        const featuresTop = getFeaturesTop();
        const base = pending ?? window.scrollY;
        const target = e.shiftKey || base >= featuresTop - 4 ? 0 : featuresTop;
        moveTo(target);
      };
      const onScroll = () => {
        if (pending !== null && Math.abs(window.scrollY - pending) < 2) pending = null;
      };
      // 터치로 직접 스크롤하면 목표 지점 기억을 지움
      const clearPending = () => {
        pending = null;
      };
      window.addEventListener("keydown", onKeyDown);
      window.addEventListener("scroll", onScroll, { passive: true });
      introRoot.addEventListener("wheel", onWheel, { passive: false });
      window.addEventListener("touchstart", clearPending, { passive: true });
      return () => {
        window.removeEventListener("keydown", onKeyDown);
        window.removeEventListener("scroll", onScroll);
        introRoot.removeEventListener("wheel", onWheel);
        window.removeEventListener("touchstart", clearPending);
      };
    },
    { scope: root }
  );
}
