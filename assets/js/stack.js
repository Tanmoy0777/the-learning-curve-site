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

    cards.forEach((card, index) => {
      const offset = index - rawIndex;
      const depth = -Math.abs(offset) * 220;
      const scale = 1 - Math.min(Math.abs(offset) * 0.06, 0.2);
      const translateY = offset * 30;
      const opacity = 1 - Math.min(Math.abs(offset) * 0.25, 0.6);

      card.style.transform = `translateY(${translateY}px) translateZ(${depth}px) scale(${scale})`;
      card.style.opacity = opacity;
      card.style.zIndex = `${100 - Math.abs(offset) * 10}`;
    });
  };

  const setup = () => {
    stacks.forEach((section) => {
      const scroller = section.querySelector(".stack-scroller");
      const cards = section.querySelectorAll(".stack-card");
      if (!scroller || !cards.length) return;
      scroller.style.height = `${cards.length * 80}vh`;
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
