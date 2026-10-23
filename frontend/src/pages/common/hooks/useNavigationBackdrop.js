import { useEffect } from "react";

// 메뉴 뒤 콘텐츠 대신, 같은 위치의 페이지 배경만 복제한다.
export default function useNavigationBackdrop(rootRef, bandSelector) {
  useEffect(() => {
    const root = rootRef.current;
    const navigation = root.querySelector(".tn");
    const bands = bandSelector ? [...root.querySelectorAll(bandSelector)] : [root];
    let frame;
    let backgrounds;

    const measure = () => {
      backgrounds = bands.map((band) => {
        const style = getComputedStyle(band);
        return { band, image: style.backgroundImage, color: style.backgroundColor };
      });
    };
    const update = () => {
      frame = undefined;
      const top = navigation.getBoundingClientRect().top;
      const current = backgrounds.find(({ band }) => {
        const rect = band.getBoundingClientRect();
        return rect.top <= top && rect.bottom > top;
      }) || backgrounds[0];
      const rect = current.band.getBoundingClientRect();
      const navRect = navigation.getBoundingClientRect();
      const offset = rect.top - navRect.top - current.band.scrollTop;
      Object.assign(navigation.style, {
        backgroundImage: current.image,
        backgroundColor: current.color === "rgba(0, 0, 0, 0)" ? getComputedStyle(root).backgroundColor : current.color,
        backgroundSize: `${current.band.clientWidth}px ${current.band.scrollHeight}px`,
        backgroundPosition: `${rect.left - navRect.left}px ${offset}px`,
        backgroundRepeat: "no-repeat",
      });
    };
    const schedule = () => {
      if (frame === undefined) frame = requestAnimationFrame(update);
    };
    const refresh = () => {
      measure();
      schedule();
    };

    measure();
    update();
    const observer = new ResizeObserver(refresh);
    bands.forEach((band) => observer.observe(band));
    window.addEventListener("scroll", schedule, { capture: true, passive: true });
    window.addEventListener("resize", refresh);
    return () => {
      if (frame !== undefined) cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("scroll", schedule, true);
      window.removeEventListener("resize", refresh);
      ["background-image", "background-color", "background-size", "background-position", "background-repeat"]
        .forEach((property) => navigation.style.removeProperty(property));
    };
  }, [rootRef, bandSelector]);
}
