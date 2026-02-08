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
    if (!track) return;

    let index = 0;
    let currentTranslate = 0;
    let prevTranslate = 0;
    let startX = 0;
    let lastX = 0;
    let lastTime = 0;
    let velocity = 0;
    let isPointerDown = false;
    const items = $$(".carousel-item", track);

    const getItemWidth = () => {
      if (!items.length) return 0;
      const styles = window.getComputedStyle(items[0]);
      const marginRight = parseFloat(styles.marginRight || "0");
      return items[0].getBoundingClientRect().width + marginRight;
    };

    const snapToIndex = (nextIndex, animate = true) => {
      const itemWidth = getItemWidth();
      index = Math.min(Math.max(nextIndex, 0), Math.max(items.length - 1, 0));
      currentTranslate = -index * itemWidth;
      prevTranslate = currentTranslate;
      track.style.transition = animate ? "transform 0.45s cubic-bezier(0.22, 0.61, 0.36, 1)" : "none";
      track.style.transform = `translateX(${currentTranslate}px)`;
    };

    const update = () => {
      snapToIndex(index, true);
    };

    if (prev) {
      prev.addEventListener("click", () => {
        index = Math.max(index - 1, 0);
        update();
      });
    }

    if (next) {
      next.addEventListener("click", () => {
        index = Math.min(index + 1, items.length - 1);
        update();
      });
    }

    const onPointerDown = (event) => {
      if (event.target.closest("button")) return;
      if (!items.length) return;
      isPointerDown = true;
      startX = event.clientX;
      lastX = startX;
      lastTime = performance.now();
      velocity = 0;
      track.style.transition = "none";
      carousel.setPointerCapture(event.pointerId);
    };

    const onPointerMove = (event) => {
      if (!isPointerDown) return;
      const currentX = event.clientX;
      const diff = currentX - startX;
      currentTranslate = prevTranslate + diff;
      track.style.transform = `translateX(${currentTranslate}px)`;
      const now = performance.now();
      velocity = (currentX - lastX) / Math.max(now - lastTime, 16);
      lastX = currentX;
      lastTime = now;
    };

    const onPointerUp = () => {
      if (!isPointerDown) return;
      isPointerDown = false;
      const itemWidth = getItemWidth();
      const momentum = velocity * 260;
      currentTranslate += momentum;
      const nextIndex = itemWidth ? Math.round(-currentTranslate / itemWidth) : 0;
      snapToIndex(nextIndex, true);
    };

    carousel.addEventListener("pointerdown", onPointerDown);
    carousel.addEventListener("pointermove", onPointerMove);
    carousel.addEventListener("pointerup", onPointerUp);
    carousel.addEventListener("pointercancel", onPointerUp);
    carousel.addEventListener("pointerleave", onPointerUp);
    window.addEventListener("resize", () => snapToIndex(index, false));
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
    const courseId = course.uid || course.id;
    const existing = items.find((item) => item.id === courseId);
    if (existing) {
      existing.qty += 1;
    } else {
      items.push({ ...course, id: courseId, qty: 1 });
    }
    saveCart(items);
    updateCartCount();
  };

  const renderVendorCourseLists = () => {
    const lists = $$('[data-course-list]');
    if (!lists.length || !window.CourseData) return;

    const vendorLookup = new Map((window.CourseData.vendors || []).map((vendor) => [vendor.id, vendor.name]));

    lists.forEach((list) => {
      const vendorId = list.dataset.vendor;
      const scope = list.dataset.vendorScope || vendorId;
      const courses = window.CourseData.courses[vendorId] || [];
      const vendorName = vendorLookup.get(vendorId) || vendorId;
      const courseMap = new Map(
        courses.map((course) => {
          const uid = `${vendorId}-${course.id}`;
          return [uid, { ...course, uid, vendorId, vendorName }];
        })
      );

      const controls = document.querySelector(`[data-vendor-filter-controls][data-vendor-scope="${scope}"]`);
      const searchInput = controls?.querySelector('[data-vendor-search]');
      const searchBtn = controls?.querySelector('[data-vendor-search-btn]');
      const levelSelect = controls?.querySelector('[data-vendor-level]');
      const deliverySelect = controls?.querySelector('[data-vendor-delivery]');
      const countEl = document.querySelector(`[data-vendor-count][data-vendor-scope="${scope}"]`);
      const emptyState = document.querySelector(`[data-vendor-empty][data-vendor-scope="${scope}"]`);

      const unique = (items) => Array.from(new Set(items)).filter(Boolean);
      if (levelSelect) {
        levelSelect.innerHTML = ['<option value="">All levels</option>']
          .concat(unique(courses.map((course) => course.level)).map((level) => `<option value="${level}">${level}</option>`))
          .join("");
      }
      if (deliverySelect) {
        deliverySelect.innerHTML = ['<option value="">All delivery types</option>']
          .concat(unique(courses.map((course) => course.delivery)).map((delivery) => `<option value="${delivery}">${delivery}</option>`))
          .join("");
      }

      const render = () => {
        const search = searchInput?.value.trim().toLowerCase() || "";
        const level = levelSelect?.value || "";
        const delivery = deliverySelect?.value || "";

        const filtered = courses.filter((course) => {
          const matchesSearch =
            !search ||
            course.title.toLowerCase().includes(search) ||
            course.focus.toLowerCase().includes(search);
          const matchesLevel = !level || course.level === level;
          const matchesDelivery = !delivery || course.delivery === delivery;
          return matchesSearch && matchesLevel && matchesDelivery;
        });

        if (countEl) {
          countEl.textContent = `${filtered.length} courses`;
        }

        list.innerHTML = filtered
          .map((course) => {
            const uid = `${vendorId}-${course.id}`;
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
                <button class="btn btn-primary" data-add-to-cart data-course-id="${uid}">Add to cart</button>
              </article>
            `;
          })
          .join("");

        if (emptyState) {
          emptyState.style.display = filtered.length ? "none" : "block";
        }

        $$("[data-add-to-cart]", list).forEach((button) => {
          button.addEventListener("click", () => {
            const courseId = button.dataset.courseId;
            const course = courseMap.get(courseId);
            if (course) addToCart(course);
          });
        });

        $$(".fade-in", list).forEach((el) => fadeObserver.observe(el));
      };

      if (searchInput) {
        searchInput.addEventListener("input", render);
        searchInput.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            render();
          }
        });
      }
      if (searchBtn) {
        searchBtn.addEventListener("click", render);
      }
      if (levelSelect) levelSelect.addEventListener("change", render);
      if (deliverySelect) deliverySelect.addEventListener("change", render);

      render();
    });
  };

  const renderCourseFinder = () => {
    const finder = $('[data-course-finder]');
    if (!finder || !window.CourseData) return;

    const controls = $('[data-course-finder-controls]');
    const searchInput = $('[data-course-search]');
    const searchButton = $('[data-course-search-btn]');
    const suggestionsEl = $('[data-course-suggestions]');
    const vendorSelect = $('[data-course-vendor]');
    const levelSelect = $('[data-course-level]');
    const deliverySelect = $('[data-course-delivery]');
    const countEl = $('[data-course-count]');
    const emptyState = $('[data-course-empty]');

    const vendorLookup = new Map((window.CourseData.vendors || []).map((vendor) => [vendor.id, vendor.name]));
    const allCourses = Object.entries(window.CourseData.courses || {}).flatMap(([vendorId, courses]) =>
      courses.map((course) => ({
        ...course,
        vendorId,
        vendorName: vendorLookup.get(vendorId) || vendorId,
        uid: `${vendorId}-${course.id}`
      }))
    );

    const unique = (items) => Array.from(new Set(items)).filter(Boolean);
    if (vendorSelect) {
      vendorSelect.innerHTML = ['<option value=\"\">All vendors</option>']
        .concat(
          (window.CourseData.vendors || []).map((vendor) => `<option value=\"${vendor.id}\">${vendor.name}</option>`)
        )
        .join("");
    }
    if (levelSelect) {
      levelSelect.innerHTML = ['<option value=\"\">All levels</option>']
        .concat(unique(allCourses.map((course) => course.level)).map((level) => `<option value=\"${level}\">${level}</option>`))
        .join("");
    }
    if (deliverySelect) {
      deliverySelect.innerHTML = ['<option value=\"\">All delivery types</option>']
        .concat(unique(allCourses.map((course) => course.delivery)).map((delivery) => `<option value=\"${delivery}\">${delivery}</option>`))
        .join("");
    }

    const hideSuggestions = () => {
      if (suggestionsEl) {
        suggestionsEl.style.display = "none";
      }
    };

    const showSuggestions = (items) => {
      if (!suggestionsEl) return;
      if (!items.length) {
        hideSuggestions();
        return;
      }
      suggestionsEl.innerHTML = items
        .map((item) => {
          if (item.type === "vendor") {
            return `
              <button class="suggestion-item" type="button" data-suggest-type="vendor" data-vendor-id="${item.vendorId}" data-label="${item.label}">
                ${item.label}
                <span>Vendor</span>
              </button>
            `;
          }
          return `
            <button class="suggestion-item" type="button" data-suggest-type="course" data-course-id="${item.uid}" data-vendor-id="${item.vendorId}" data-label="${item.label}">
              ${item.label}
              <span>${item.meta}</span>
            </button>
          `;
        })
        .join("");
      suggestionsEl.style.display = "block";
    };

    const updateSuggestions = () => {
      const query = searchInput?.value.trim().toLowerCase() || "";
      if (!query || query.length < 2) {
        hideSuggestions();
        return;
      }
      const vendorMatches = (window.CourseData.vendors || [])
        .filter((vendor) => vendor.name.toLowerCase().includes(query))
        .slice(0, 3)
        .map((vendor) => ({
          type: "vendor",
          vendorId: vendor.id,
          label: vendor.name
        }));

      const courseMatches = allCourses
        .filter(
          (course) =>
            course.title.toLowerCase().includes(query) ||
            course.focus.toLowerCase().includes(query) ||
            course.vendorName.toLowerCase().includes(query)
        )
        .slice(0, 6)
        .map((course) => ({
          type: "course",
          uid: course.uid,
          vendorId: course.vendorId,
          label: course.title,
          meta: course.vendorName
        }));

      showSuggestions([...vendorMatches, ...courseMatches]);
    };

    const render = () => {
      const search = searchInput?.value.trim().toLowerCase() || "";
      const vendor = vendorSelect?.value || "";
      const level = levelSelect?.value || "";
      const delivery = deliverySelect?.value || "";

      const filtered = allCourses.filter((course) => {
        const matchesSearch =
          !search ||
          course.title.toLowerCase().includes(search) ||
          course.focus.toLowerCase().includes(search) ||
          course.vendorName.toLowerCase().includes(search);
        const matchesVendor = !vendor || course.vendorId === vendor;
        const matchesLevel = !level || course.level === level;
        const matchesDelivery = !delivery || course.delivery === delivery;
        return matchesSearch && matchesVendor && matchesLevel && matchesDelivery;
      });

      if (countEl) {
        countEl.textContent = `${filtered.length} courses`;
      }

      finder.innerHTML = filtered
        .map((course) => {
          return `
            <article class="course-card fade-in">
              <div class="tag">${course.vendorName}</div>
              <h3>${course.title}</h3>
              <p>${course.focus}</p>
              <div class="course-meta">
                <span>${course.level}</span>
                <span>${course.duration}</span>
              </div>
              <div class="price">$${course.price.toLocaleString()}</div>
              <button class="btn btn-primary" data-add-to-cart data-course-id="${course.uid}">Add to cart</button>
            </article>
          `;
        })
        .join("");

      if (emptyState) {
        emptyState.style.display = filtered.length ? "none" : "block";
      }

      $$("[data-add-to-cart]", finder).forEach((button) => {
        button.addEventListener("click", () => {
          const courseId = button.dataset.courseId;
          const course = allCourses.find((item) => item.uid === courseId);
          if (course) addToCart(course);
        });
      });

      $$(".fade-in", finder).forEach((el) => fadeObserver.observe(el));
    };

    if (searchInput) {
      searchInput.addEventListener("input", () => {
        updateSuggestions();
        render();
      });
      searchInput.addEventListener("focus", updateSuggestions);
      searchInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          render();
          hideSuggestions();
        }
      });
    }

    if (searchButton) {
      searchButton.addEventListener("click", () => {
        render();
        hideSuggestions();
      });
    }

    if (vendorSelect) vendorSelect.addEventListener("change", render);
    if (levelSelect) levelSelect.addEventListener("change", render);
    if (deliverySelect) deliverySelect.addEventListener("change", render);

    if (suggestionsEl) {
      suggestionsEl.addEventListener("click", (event) => {
        const target = event.target.closest(".suggestion-item");
        if (!target) return;
        const type = target.dataset.suggestType;
        const label = target.dataset.label || "";
        const vendorId = target.dataset.vendorId || "";
        if (type === "vendor") {
          if (vendorSelect) vendorSelect.value = vendorId;
          if (searchInput) searchInput.value = label;
        }
        if (type === "course") {
          if (searchInput) searchInput.value = label;
          if (vendorSelect) vendorSelect.value = vendorId || vendorSelect.value;
        }
        render();
        hideSuggestions();
      });
    }

    if (controls) {
      document.addEventListener("click", (event) => {
        if (!controls.contains(event.target)) {
          hideSuggestions();
        }
      });
    }

    render();
  };

  const initLmsWizard = () => {
    const form = $('[data-lms-form]');
    if (!form || !window.CourseData) return;

    const steps = Array.from(form.querySelectorAll('[data-lms-step]'));
    const indicators = Array.from(document.querySelectorAll('[data-step-indicator]'));
    const nextButtons = Array.from(form.querySelectorAll('[data-lms-next]'));
    const backButtons = Array.from(form.querySelectorAll('[data-lms-back]'));
    const recommendationsEl = form.querySelector('[data-lms-recommendations]');
    const audienceField = form.querySelector('select[name="audience"]');
    const focusField = form.querySelector('select[name="focus_area"]');

    const vendorLookup = new Map((window.CourseData.vendors || []).map((vendor) => [vendor.id, vendor.name]));
    const allCourses = Object.entries(window.CourseData.courses || {}).flatMap(([vendorId, courses]) =>
      courses.map((course) => ({
        ...course,
        vendorId,
        vendorName: vendorLookup.get(vendorId) || vendorId,
        uid: `${vendorId}-${course.id}`
      }))
    );

    const focusMap = {
      "Cloud modernization": {
        vendors: ["microsoft", "aws", "google"],
        keywords: ["Cloud", "Architect", "Administrator", "Engineer"]
      },
      "AI adoption": {
        vendors: ["ai-certs", "adoptify-ai", "microsoft"],
        keywords: ["AI", "Prompt", "LLM", "Adoptify"]
      },
      "Sales enablement": {
        vendors: ["microsoft", "ai-certs", "pmi"],
        keywords: ["Power", "BI", "AI", "Agile", "Portfolio"]
      },
      "Security & compliance": {
        vendors: ["cisco", "aws", "microsoft", "google"],
        keywords: ["Security", "Risk", "Compliance"]
      }
    };

    const parseDuration = (value) => {
      const match = value?.match(/(\\d+)/);
      return match ? Number(match[1]) : 0;
    };

    const getRecommendations = () => {
      const focus = focusField?.value || "";
      const audience = audienceField?.value || "";
      const timeline = form.querySelector('select[name="timeline"]')?.value || "";
      const config = focusMap[focus] || { vendors: [], keywords: [] };

      const scored = allCourses.map((course) => {
        let score = 0;
        const reasons = [];
        if (config.vendors.includes(course.vendorId)) {
          score += 4;
          reasons.push("Focus match");
        }
        const keywordHits = config.keywords.filter(
          (keyword) => course.title.includes(keyword) || course.focus.includes(keyword)
        );
        if (keywordHits.length) {
          score += keywordHits.length * 2;
          reasons.push("Skill alignment");
        }
        if (audience === "Individual learners" && course.vendorId === "ai-certs") {
          score += 4;
          reasons.push("Ideal for individuals");
        }
        if (audience === "Executives" && ["adoptify-ai", "pmi"].includes(course.vendorId)) {
          score += 4;
          reasons.push("Executive ready");
        }
        if (audience === "Enterprise teams" && ["microsoft", "aws", "google", "cisco", "pmi"].includes(course.vendorId)) {
          score += 3;
          reasons.push("Enterprise fit");
        }
        const durationDays = parseDuration(course.duration);
        if (timeline.startsWith("Immediate") && durationDays && durationDays <= 2) {
          score += 2;
          reasons.push("Fast-track");
        }
        if (timeline.startsWith("Next quarter") && durationDays && durationDays <= 4) {
          score += 1;
          reasons.push("Quarter-ready");
        }
        return { ...course, score, reasons: reasons.join(" • ") || "AI curated fit" };
      });

      return scored
        .sort((a, b) => b.score - a.score)
        .slice(0, 6);
    };

    const renderRecommendations = () => {
      if (!recommendationsEl) return;
      const recommendations = getRecommendations();
      recommendationsEl.innerHTML = recommendations
        .map((course) => {
          const label = `${course.vendorName} • ${course.title}`;
          return `
            <label class="course-card recommend-card">
              <div class="tag">${course.vendorName}</div>
              <h3>${course.title}</h3>
              <p>${course.focus}</p>
              <div class="course-meta">
                <span>${course.level}</span>
                <span>${course.duration}</span>
              </div>
              <div class="ai-reason">${course.reasons}</div>
              <div class="price">$${course.price.toLocaleString()}</div>
              <input type="checkbox" name="recommended_courses" value="${label}" checked />
            </label>
          `;
        })
        .join("");

      $$(".fade-in", recommendationsEl).forEach((el) => fadeObserver.observe(el));
    };

    let currentStep = 1;
    const showStep = (step) => {
      currentStep = step;
      steps.forEach((panel) => {
        panel.style.display = panel.dataset.lmsStep === String(step) ? "grid" : "none";
      });
      indicators.forEach((indicator) => {
        indicator.classList.toggle("is-active", indicator.dataset.stepIndicator === String(step));
      });
      if (step === 3) {
        renderRecommendations();
      }
    };

    const validateStep = (step) => {
      const panel = steps.find((item) => item.dataset.lmsStep === String(step));
      if (!panel) return true;
      const fields = Array.from(panel.querySelectorAll("[required]"));
      for (const field of fields) {
        if (!field.checkValidity()) {
          field.reportValidity();
          return false;
        }
      }
      return true;
    };

    nextButtons.forEach((button) => {
      button.addEventListener("click", () => {
        if (!validateStep(currentStep)) return;
        showStep(Math.min(currentStep + 1, steps.length));
      });
    });

    backButtons.forEach((button) => {
      button.addEventListener("click", () => {
        showStep(Math.max(currentStep - 1, 1));
      });
    });

    if (audienceField) {
      audienceField.addEventListener("change", () => {
        if (currentStep === 3) renderRecommendations();
      });
    }
    if (focusField) {
      focusField.addEventListener("change", () => {
        if (currentStep === 3) renderRecommendations();
      });
    }

    showStep(1);
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
            <div class="tag">${item.vendorName || item.vendorId || "Course"}</div>
            <h3>${item.title}</h3>
            <p>${item.focus}</p>
            <div class="course-meta">
              <span>${item.level || "Level"}</span>
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
      if (Object.prototype.hasOwnProperty.call(data, key)) {
        if (Array.isArray(data[key])) {
          data[key].push(value);
        } else {
          data[key] = [data[key], value];
        }
      } else {
        data[key] = value;
      }
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
  renderVendorCourseLists();
  renderCourseFinder();
  initLmsWizard();
  renderCart();
  renderCheckout();
})();
