(() => {
  const stacks = document.querySelectorAll("[data-stack]");
  if (!stacks.length) return;

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

  const updateStack = (section) => {
    const scroller = section.querySelector(".stack-scroller");
    const cards = Array.from(section.querySelectorAll(".stack-card"));
    if (!scroller || !cards.length) return;

    const sectionTop = section.offsetTop;
    const sectionHeight = scroller.offsetHeight;
    const maxScroll = sectionHeight - window.innerHeight;
    const scrollY = window.scrollY - sectionTop;
    const progress = clamp(scrollY / Math.max(maxScroll, 1), 0, 1);
    const total = cards.length - 1;
    const rawIndex = progress * total;
    const activeIndex = Math.round(rawIndex);
    const isMobile = window.innerWidth < 768;
    const depthStep = isMobile ? 160 : 220;
    const scaleStep = isMobile ? 0.085 : 0.06;
    const translateStep = isMobile ? 42 : 30;
    const opacityStep = isMobile ? 0.22 : 0.25;

    cards.forEach((card, index) => {
      const offset = index - rawIndex;
      const depth = -Math.abs(offset) * depthStep;
      const scale = 1 - Math.min(Math.abs(offset) * scaleStep, 0.22);
      const translateY = offset * translateStep;
      const opacity = 1 - Math.min(Math.abs(offset) * opacityStep, 0.6);

      card.style.transform = `translateY(${translateY}px) translateZ(${depth}px) scale(${scale})`;
      card.style.opacity = opacity;
      card.style.zIndex = `${100 - Math.abs(offset) * 10}`;
      card.classList.toggle("is-active", index === activeIndex);
    });
  };

  const setup = () => {
    stacks.forEach((section) => {
      const scroller = section.querySelector(".stack-scroller");
      const cards = section.querySelectorAll(".stack-card");
      if (!scroller || !cards.length) return;
      const heightUnit = window.innerWidth < 768 ? 70 : 80;
      scroller.style.height = `${cards.length * heightUnit}vh`;
      updateStack(section);
    });
  };

  let ticking = false;
  const onScroll = () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        stacks.forEach(updateStack);
        ticking = false;
      });
      ticking = true;
    }
  };

  window.addEventListener("scroll", onScroll);
  window.addEventListener("resize", setup);
  setup();
})();
