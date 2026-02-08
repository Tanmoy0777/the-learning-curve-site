(() => {
  const canvas = document.getElementById("starfield");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  let width = 0;
  let height = 0;
  let dpr = Math.min(window.devicePixelRatio || 1, 2);
  let lastTime = performance.now();
  let mouseX = 0;
  let mouseY = 0;
  let offsetX = 0;
  let offsetY = 0;
  let scrollBoost = 0;
  let lastScrollY = window.scrollY;

  const layers = [
    { count: 1700, speed: 0.12, size: 1.1, alpha: 0.42, parallax: 25 },
    { count: 1100, speed: 0.24, size: 1.9, alpha: 0.68, parallax: 55 },
    { count: 700, speed: 0.38, size: 2.7, alpha: 0.9, parallax: 90 }
  ];

  const stars = [];
  const sprites = new Map();

  const createSprite = (size, alpha) => {
    const key = `${size}-${alpha}`;
    if (sprites.has(key)) return sprites.get(key);

    const sprite = document.createElement("canvas");
    const radius = size * 6;
    sprite.width = radius;
    sprite.height = radius;
    const sctx = sprite.getContext("2d");
    const gradient = sctx.createRadialGradient(
      radius / 2,
      radius / 2,
      0,
      radius / 2,
      radius / 2,
      radius / 2
    );
    gradient.addColorStop(0, `rgba(255,255,255,${alpha})`);
    gradient.addColorStop(0.35, `rgba(180,200,255,${alpha * 0.65})`);
    gradient.addColorStop(0.7, `rgba(120,140,220,${alpha * 0.25})`);
    gradient.addColorStop(1, "rgba(0,0,0,0)");
    sctx.fillStyle = gradient;
    sctx.beginPath();
    sctx.arc(radius / 2, radius / 2, radius / 2, 0, Math.PI * 2);
    sctx.fill();

    sprites.set(key, sprite);
    return sprite;
  };

  const randomStar = (layer) => {
    const spread = 1.2;
    return {
      x: (Math.random() * 2 - 1) * spread,
      y: (Math.random() * 2 - 1) * spread,
      z: Math.random() * 0.9 + 0.1,
      layer
    };
  };

  const initStars = () => {
    stars.length = 0;
    layers.forEach((layer) => {
      for (let i = 0; i < layer.count; i += 1) {
        stars.push(randomStar(layer));
      }
    });
  };

  const resize = () => {
    width = window.innerWidth;
    height = window.innerHeight;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };

  const draw = (timestamp) => {
    const delta = Math.min((timestamp - lastTime) / 1000, 0.05);
    lastTime = timestamp;

    ctx.clearRect(0, 0, width, height);
    ctx.globalCompositeOperation = "lighter";

    const centerX = width / 2;
    const centerY = height / 2;
    const scale = Math.min(width, height) * 0.55;

    offsetX += (mouseX - offsetX) * 0.06;
    offsetY += (mouseY - offsetY) * 0.06;

    scrollBoost *= 0.9;

    for (let i = 0; i < stars.length; i += 1) {
      const star = stars[i];
      const layer = star.layer;
      const speed = layer.speed + scrollBoost;
      star.z -= speed * delta;
      if (star.z <= 0.05) {
        star.x = (Math.random() * 2 - 1) * 1.2;
        star.y = (Math.random() * 2 - 1) * 1.2;
        star.z = 1;
      }

      const depth = 1 / star.z;
      const px = star.x * depth * scale + centerX + offsetX * layer.parallax;
      const py = star.y * depth * scale + centerY + offsetY * layer.parallax;

      if (px < -80 || px > width + 80 || py < -80 || py > height + 80) {
        continue;
      }

      const size = layer.size * depth;
      const sprite = createSprite(size, layer.alpha);
      ctx.drawImage(sprite, px - size * 3, py - size * 3, size * 6, size * 6);
    }

    ctx.globalCompositeOperation = "source-over";
    requestAnimationFrame(draw);
  };

  window.addEventListener("mousemove", (event) => {
    mouseX = (event.clientX / width - 0.5) * 2;
    mouseY = (event.clientY / height - 0.5) * 2;
  });

  window.addEventListener("scroll", () => {
    const current = window.scrollY;
    const delta = current - lastScrollY;
    scrollBoost = Math.max(Math.min(scrollBoost + delta * 0.0025, 1.2), -0.6);
    lastScrollY = current;
  });

  window.addEventListener("resize", () => {
    resize();
  });

  resize();
  initStars();
  requestAnimationFrame(draw);
})();
