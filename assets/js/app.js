(() => {
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));

  const navToggle = $("[data-nav-toggle]");
  const nav = $(".nav");
  if (navToggle && nav) {
    navToggle.addEventListener("click", () => {
      nav.classList.toggle("open");
    });
  }

  const dropdownToggle = $("[data-dropdown-toggle]");
  if (dropdownToggle) {
    dropdownToggle.addEventListener("click", (event) => {
      if (window.innerWidth < 900) {
        event.preventDefault();
        dropdownToggle.parentElement.classList.toggle("open");
      }
    });
  }

  const countUp = (el) => {
    const target = Number(el.dataset.count || "0");
    const suffix = el.dataset.suffix || "";
    const prefix = el.dataset.prefix || "";
    const duration = 1400;
    const start = performance.now();

    const animate = (time) => {
      const progress = Math.min((time - start) / duration, 1);
      const value = Math.floor(target * progress);
      el.textContent = `${prefix}${value.toLocaleString()}${suffix}`;
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  };

  const counterObserver = new IntersectionObserver(
    (entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          countUp(entry.target);
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.5 }
  );

  $$('[data-count]').forEach((el) => counterObserver.observe(el));

  const fadeObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("in-view");
        }
      });
    },
    { threshold: 0.12 }
  );

  $$(".fade-in").forEach((el) => fadeObserver.observe(el));

  $$('[data-carousel]').forEach((carousel) => {
    const track = $(".carousel-track", carousel);
    const prev = $("[data-carousel-prev]", carousel);
    const next = $("[data-carousel-next]", carousel);
    if (!track || !prev || !next) return;

    let index = 0;
    const items = $$(".carousel-item", track);

    const update = () => {
      const offset = items[0].offsetWidth + 20;
      track.style.transform = `translateX(${-index * offset}px)`;
    };

    prev.addEventListener("click", () => {
      index = Math.max(index - 1, 0);
      update();
    });

    next.addEventListener("click", () => {
      index = Math.min(index + 1, items.length - 1);
      update();
    });
  });

  const getCart = () => {
    try {
      return JSON.parse(localStorage.getItem("tlc-cart") || "[]");
    } catch (error) {
      return [];
    }
  };

  const saveCart = (items) => {
    localStorage.setItem("tlc-cart", JSON.stringify(items));
  };

  const updateCartCount = () => {
    const items = getCart();
    const total = items.reduce((sum, item) => sum + item.qty, 0);
    $$('[data-cart-count]').forEach((el) => {
      el.textContent = total;
    });
  };

  const addToCart = (course) => {
    const items = getCart();
    const existing = items.find((item) => item.id === course.id);
    if (existing) {
      existing.qty += 1;
    } else {
      items.push({ ...course, qty: 1 });
    }
    saveCart(items);
    updateCartCount();
  };

  const renderCourseList = () => {
    const list = $('[data-course-list]');
    if (!list || !window.CourseData) return;
    const vendorId = list.dataset.vendor;
    const courses = window.CourseData.courses[vendorId] || [];
    list.innerHTML = courses
      .map((course) => {
        return `
          <article class="course-card fade-in">
            <div class="tag">${course.level}</div>
            <h3>${course.title}</h3>
            <p>${course.focus}</p>
            <div class="course-meta">
              <span>${course.duration}</span>
              <span>${course.delivery}</span>
            </div>
            <div class="price">$${course.price.toLocaleString()}</div>
            <button class="btn btn-primary" data-add-to-cart data-course-id="${course.id}">Add to cart</button>
          </article>
        `;
      })
      .join("");

    $$("[data-add-to-cart]", list).forEach((button) => {
      button.addEventListener("click", () => {
        const courseId = button.dataset.courseId;
        const course = courses.find((item) => item.id === courseId);
        if (course) addToCart(course);
      });
    });

    $$(".fade-in", list).forEach((el) => fadeObserver.observe(el));
  };

  const renderCart = () => {
    const cartList = $('[data-cart-list]');
    const cartTotal = $('[data-cart-total]');
    if (!cartList) return;

    const items = getCart();
    if (!items.length) {
      cartList.innerHTML = "<p>Your cart is currently empty.</p>";
      if (cartTotal) cartTotal.textContent = "$0";
      return;
    }

    cartList.innerHTML = items
      .map((item) => {
        return `
          <div class="course-card">
            <div class="tag">${item.level}</div>
            <h3>${item.title}</h3>
            <p>${item.focus}</p>
            <div class="course-meta">
              <span>Qty ${item.qty}</span>
              <span>$${item.price.toLocaleString()}</span>
            </div>
            <button class="btn btn-outline" data-remove="${item.id}">Remove</button>
          </div>
        `;
      })
      .join("");

    const total = items.reduce((sum, item) => sum + item.price * item.qty, 0);
    if (cartTotal) cartTotal.textContent = `$${total.toLocaleString()}`;

    $$("[data-remove]", cartList).forEach((button) => {
      button.addEventListener("click", () => {
        const id = button.dataset.remove;
        const updated = getCart().filter((item) => item.id !== id);
        saveCart(updated);
        renderCart();
        updateCartCount();
      });
    });
  };

  const renderCheckout = () => {
    const summary = $('[data-checkout-summary]');
    if (!summary) return;
    const items = getCart();
    const total = items.reduce((sum, item) => sum + item.price * item.qty, 0);
    summary.innerHTML = items
      .map((item) => `<div class="course-meta"><span>${item.title}</span><span>$${(item.price * item.qty).toLocaleString()}</span></div>`)
      .join("");

    const totalEl = $('[data-checkout-total]');
    if (totalEl) totalEl.textContent = `$${total.toLocaleString()}`;

    const form = $('[data-checkout-form]');
    if (form) {
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const payload = {
          type: form.dataset.leadType || "checkout",
          page: window.location.pathname,
          timestamp: new Date().toISOString(),
          data: serializeForm(form),
          cart: items,
          total
        };
        await postToN8N(payload);
        form.reset();
        saveCart([]);
        updateCartCount();
        showFormMessage(form, "<strong>Order received.</strong> Our team will confirm scheduling within 1 business day.");
      });
    }
  };

  const N8N_WEBHOOK_URL = window.N8N_WEBHOOK_URL || "";

  const serializeForm = (form) => {
    const data = {};
    new FormData(form).forEach((value, key) => {
      data[key] = value;
    });
    return data;
  };

  const showFormMessage = (form, message) => {
    const existing = form.querySelector(".form-message");
    if (existing) existing.remove();
    const note = document.createElement("p");
    note.className = "form-message";
    note.innerHTML = message;
    form.appendChild(note);
  };

  const postToN8N = async (payload) => {
    if (!N8N_WEBHOOK_URL) {
      return { skipped: true };
    }
    try {
      const response = await fetch(N8N_WEBHOOK_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        throw new Error(`Webhook failed: ${response.status}`);
      }
      return { ok: true };
    } catch (error) {
      console.error(error);
      return { ok: false };
    }
  };

  const leadForms = $$('[data-lead-form]');
  leadForms.forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = {
        type: form.dataset.leadType || "lead",
        page: window.location.pathname,
        timestamp: new Date().toISOString(),
        data: serializeForm(form)
      };
      await postToN8N(payload);
      form.reset();
      showFormMessage(form, "<strong>Thanks.</strong> A learning strategist will reach out within 24 hours.");
    });
  });

  updateCartCount();
  renderCourseList();
  renderCart();
  renderCheckout();
})();
