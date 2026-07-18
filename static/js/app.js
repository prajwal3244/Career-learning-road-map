/* =========================================================================
   THE DATA & AI TRANSIT — frontend logic
   Fetches curriculum config, builds the assessment UI, requests a personalized
   route, and tracks station completion in localStorage (keyed on stable stage
   ids so progress survives re-assessment). Careers render as transit "lines".
   ========================================================================= */
(() => {
  "use strict";

  const state = { skills: [], careers: [], selectedCareer: null, roadmap: null, progressKey: null };

  // Each career is a transit "line" with its own colour (CSS custom props).
  const LINE_COLORS = {
    "data-analyst": "var(--l1)", "data-scientist": "var(--l2)", "ml-engineer": "var(--l3)",
    "ai-engineer": "var(--l4)", "data-engineer": "var(--l5)",
  };
  const lineColor = (id, i) => LINE_COLORS[id] || `var(--l${(i % 5) + 1})`;

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const escapeHTML = (str) =>
    String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const isSafeHttpUrl = (url) => {
    try {
      const u = new URL(url, window.location.origin);
      return u.protocol === "https:" || u.protocol === "http:";
    } catch { return false; }
  };

  // localStorage can throw entirely (Safari private mode, blocked cookies).
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* best-effort */ } },
    remove(k) { try { localStorage.removeItem(k); } catch { /* best-effort */ } },
  };

  const prefersReduced = () => {
    try { return matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; }
  };
  const scrollToEl = (sel) => {
    const el = $(sel);
    if (el) el.scrollIntoView({ behavior: prefersReduced() ? "auto" : "smooth", block: "start" });
  };

  /* ---------------------------- Theme ---------------------------------- */
  function initTheme() {
    const saved = store.get("fg-theme");
    if (saved === "light" || saved === "dark") document.documentElement.setAttribute("data-theme", saved);
    syncThemeUI();
    $("#theme-toggle").addEventListener("click", () => {
      const isDark = document.documentElement.getAttribute("data-theme") === "dark";
      const next = isDark ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      store.set("fg-theme", next);
      syncThemeUI();
    });
  }
  function syncThemeUI() {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const btn = $("#theme-toggle");
    btn.setAttribute("aria-pressed", String(isDark));
    btn.setAttribute("aria-label", isDark ? "Switch to day service (light mode)" : "Switch to night service (dark mode)");
    $(".toggle__label", btn).textContent = isDark ? "Day" : "Night";
  }

  /* ---------------------------- Load config ---------------------------- */
  async function loadConfig() {
    const res = await fetch("/api/config");
    if (!res.ok) throw new Error(`Server responded ${res.status}`);
    const data = await res.json();
    state.skills = data.skills || [];
    state.careers = data.careers || [];
    renderCareersGrid();
    renderSkillsForm();
    renderCareerSelect();
    const t = $("#stat-tracks"), s = $("#stat-skills");
    if (t) t.textContent = state.careers.length;
    if (s) s.textContent = state.skills.length;
  }

  function showConfigError(msg) {
    const html = `<p class="err">${escapeHTML(msg)}</p>`;
    $("#careers-grid").innerHTML = html;
    $("#skills-form").innerHTML = html;
    $("#career-select").innerHTML = "";
    $("#builder-error").textContent = msg;
  }

  /* ---------------------------- Lines (careers) ------------------------ */
  function renderCareersGrid() {
    const grid = $("#careers-grid");
    if (!state.careers.length) { grid.innerHTML = `<p class="err">No lines are running yet.</p>`; return; }
    grid.innerHTML = state.careers
      .map((c, i) => `
        <article class="line-card" data-career="${escapeHTML(c.id)}" role="button" tabindex="0"
                 style="--lc: ${lineColor(c.id, i)}" aria-label="Select the ${escapeHTML(c.title)} line and plan a journey">
          <div class="line-card__head">
            <span class="line-card__bullet"></span>
            <div>
              <div class="line-card__name">${escapeHTML(c.icon)} ${escapeHTML(c.title)} Line</div>
              <div class="stop__no">Line ${String(i + 1).padStart(2, "0")} · calls at ${c.core_skills ? c.core_skills.length : "several"} stations</div>
            </div>
          </div>
          <p class="line-card__tag">${escapeHTML(c.tagline)}</p>
          <div class="line-card__meta">
            <span class="tag tag--hot">${escapeHTML(c.demand)} demand</span>
            <span class="tag">${escapeHTML(c.avg_salary_us)}</span>
            <span class="tag">${escapeHTML(c.avg_salary_in)}</span>
          </div>
        </article>`)
      .join("");

    const pick = (id) => { selectCareer(id); scrollToEl("#build"); };
    $$(".line-card", grid).forEach((card) => {
      const id = card.dataset.career;
      card.addEventListener("click", () => pick(id));
      card.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(id); } });
    });
  }

  /* ---------------------------- Skills form ---------------------------- */
  function renderSkillsForm() {
    const form = $("#skills-form");
    if (!state.skills.length) { form.innerHTML = `<p class="err">No skills are configured.</p>`; return; }
    form.innerHTML = state.skills
      .map((s) => `
        <div class="gauge">
          <div class="gauge__top">
            <label class="gauge__name" for="skill-${escapeHTML(s.id)}"><span>${escapeHTML(s.icon)}</span> ${escapeHTML(s.name)}</label>
            <span class="gauge__val" id="val-${escapeHTML(s.id)}">0</span>
          </div>
          <input type="range" id="skill-${escapeHTML(s.id)}" min="0" max="100" value="0" step="5"
                 data-skill="${escapeHTML(s.id)}" aria-describedby="val-${escapeHTML(s.id)}" title="${escapeHTML(s.description)}" />
        </div>`)
      .join("");

    $$('input[type="range"]', form).forEach((input) => {
      input.addEventListener("input", () => { $(`#val-${CSS.escape(input.dataset.skill)}`).textContent = input.value; });
    });
  }

  function readSkillScores() {
    const scores = {};
    $$('#skills-form input[type="range"]').forEach((input) => { scores[input.dataset.skill] = Number(input.value); });
    return scores;
  }

  /* ---------------------------- Career select -------------------------- */
  function renderCareerSelect() {
    const box = $("#career-select");
    box.innerHTML = state.careers
      .map((c, i) => `
        <label class="pick" data-career="${escapeHTML(c.id)}" style="--lc: ${lineColor(c.id, i)}">
          <input type="radio" name="career" value="${escapeHTML(c.id)}" />
          <span class="pick__bullet"></span>
          <span>
            <span class="pick__title">${escapeHTML(c.title)} Line</span><br />
            <span class="pick__tag">${escapeHTML(c.demand)} · ${escapeHTML(c.avg_salary_us)}</span>
          </span>
        </label>`)
      .join("");
    $$('input[name="career"]', box).forEach((radio) => radio.addEventListener("change", () => selectCareer(radio.value)));
  }

  function selectCareer(id) {
    state.selectedCareer = id;
    $$(".pick").forEach((opt) => opt.classList.toggle("is-selected", opt.dataset.career === id));
    const radio = $(`input[name="career"][value="${CSS.escape(id)}"]`);
    if (radio) radio.checked = true;
    $("#generate-btn").disabled = false;
    $("#builder-error").textContent = "";
  }

  /* ---------------------------- Generate ------------------------------- */
  async function generateRoadmap() {
    if (!state.selectedCareer) { $("#builder-error").textContent = "Pick a destination first."; return; }
    const btn = $("#generate-btn");
    btn.disabled = true; btn.textContent = "Plotting…";
    try {
      const res = await fetch("/api/roadmap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ career: state.selectedCareer, skills: readSkillScores() }),
      });
      if (!res.ok) {
        let msg = `Request failed (${res.status})`;
        try { msg = (await res.json()).error || msg; } catch { /* non-JSON error page */ }
        throw new Error(msg);
      }
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      state.roadmap = data;
      state.progressKey = `fg-progress-${data.career.id}`;
      renderRoadmap(data);
      $("#roadmap-section").classList.remove("is-hidden");
      $("#nav-roadmap").classList.remove("is-hidden");
      scrollToEl("#roadmap-section");
    } catch (err) {
      $("#builder-error").textContent = `Could not plot route: ${err.message}`;
    } finally {
      btn.disabled = false; btn.textContent = "Plot my route →";
    }
  }

  /* ---------------------------- Render roadmap ------------------------- */
  function renderRoadmap(data) {
    const c = data.career;
    // Theme the whole route in this line's colour.
    const idx = state.careers.findIndex((x) => x.id === c.id);
    const lc = lineColor(c.id, idx < 0 ? 0 : idx);
    $("#roadmap-section").style.setProperty("--rc", lc);
    $("#timeline").style.setProperty("--lc", lc);

    $("#roadmap-title").innerHTML = `${escapeHTML(c.icon)} The <em>${escapeHTML(c.title)}</em> Line`;
    $("#roadmap-tagline").textContent = c.tagline;

    const s = data.summary;
    const stats = [
      { val: s.total_stages, label: "milestones" },
      { val: `${s.total_hours}h`, label: "est. effort" },
      { val: `${s.weeks_full_time}w`, label: "full-time · 40h/wk" },
      { val: `${s.weeks_part_time}w`, label: "part-time · 10h/wk" },
    ];
    $("#summary-cards").innerHTML = stats
      .map((x) => `<div class="stat"><div class="stat__val">${escapeHTML(x.val)}</div><div class="stat__label">${escapeHTML(x.label)}</div></div>`)
      .join("");

    // Skills already mastered — acknowledge rather than silently drop.
    const mastered = $("#mastered");
    if (s.skills_mastered && s.skills_mastered.length) {
      mastered.innerHTML =
        `<div class="mastered__h">Already mastered — skipped on your route</div>` +
        `<div class="mastered__chips">${s.skills_mastered.map((m) => `<span class="mastered__chip">✓ ${escapeHTML(m)}</span>`).join("")}</div>`;
      mastered.classList.remove("is-hidden");
    } else {
      mastered.classList.add("is-hidden");
    }

    const origin = `<li class="stop stop--origin"><div class="stop__marker"></div><div class="origin-card"><b>◉ You are here — today</b></div></li>`;
    $("#timeline").innerHTML = origin + data.stages.map(renderStop).join("");

    $$(".stop:not(.stop--origin)", $("#timeline")).forEach((stopEl) => {
      const toggle = $(".stop__toggle", stopEl);
      const body = $(".stop__body", stopEl);
      const checkbox = $(".stop__check input", stopEl);
      const openClose = () => {
        const open = stopEl.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", String(open));
        toggle.setAttribute("aria-label", open ? "Collapse details" : "Expand details");
        body.setAttribute("aria-hidden", String(!open));
      };
      toggle.addEventListener("click", openClose);
      $(".stop__title", stopEl).addEventListener("click", openClose);
      checkbox.addEventListener("change", () => {
        stopEl.classList.toggle("is-done", checkbox.checked);
        saveProgress(); updateProgress();
      });
    });

    initMeter();
    loadProgress();
    updateProgress();
    bindRoadmapActions();
  }

  function renderStop(stage) {
    const badges = [];
    const typeLabel = { skill: stage.level || "Skill", capstone: "Capstone", closing: "Career" }[stage.type] || "Step";
    badges.push(`<span class="badge badge--type">${escapeHTML(typeLabel)}</span>`);
    if (stage.hours) badges.push(`<span class="badge badge--hours">${escapeHTML(stage.hours)}h</span>`);
    if (stage.type === "skill" && typeof stage.current_score === "number")
      badges.push(`<span class="badge">now ${escapeHTML(stage.current_score)} → aim ${escapeHTML(stage.target_score)}</span>`);

    const objectives = (stage.objectives || []).map((o) => `<li>${escapeHTML(o)}</li>`).join("");
    const resources = (stage.resources || []).map((r) => {
      const inner =
        `<span class="res__type">${escapeHTML(r.type || "Link")}</span>` +
        `<span class="res__title">${escapeHTML(r.title)}</span>` +
        `<span class="res__cost ${/paid/i.test(r.cost || "") ? "is-paid" : ""}">${escapeHTML(r.cost || "")}</span>`;
      return isSafeHttpUrl(r.url)
        ? `<li><a class="res" href="${escapeHTML(r.url)}" target="_blank" rel="noopener noreferrer">${inner}</a></li>`
        : `<li><span class="res">${inner}</span></li>`;
    }).join("");

    const brief = stage.project ? `<div class="brief"><b>Project on arrival</b>${escapeHTML(stage.project)}</div>` : "";
    const bodyId = `stop-body-${escapeHTML(stage.key)}`;
    const interchange = stage.type === "capstone" || stage.type === "closing" ? " stop--interchange" : "";
    const stopLabel = stage.type === "closing" ? "Terminus" : stage.type === "capstone" ? "Interchange" : `Stop ${String(stage.step).padStart(2, "0")}`;

    return `
      <li class="stop${interchange}" data-step="${escapeHTML(stage.key)}">
        <div class="stop__marker"></div>
        <div class="stop__card">
          <div class="stop__head">
            <label class="stop__check"><input type="checkbox" aria-label="Mark reached: ${escapeHTML(stage.title)}" /></label>
            <div class="stop__heading">
              <div class="stop__no">${escapeHTML(stage.icon || "•")} ${escapeHTML(stopLabel)}</div>
              <h3 class="stop__title">${escapeHTML(stage.title)}</h3>
              <div class="stop__badges">${badges.join("")}</div>
              ${stage.why ? `<p class="stop__why">${escapeHTML(stage.why)}</p>` : ""}
            </div>
            <button class="stop__toggle" type="button" aria-expanded="false" aria-controls="${bodyId}" aria-label="Expand details">▾</button>
          </div>
          <div class="stop__body" id="${bodyId}" aria-hidden="true">
            ${objectives ? `<div class="stop__sec">What you'll learn</div><ul class="stop__list">${objectives}</ul>` : ""}
            ${resources ? `<div class="stop__sec">Resources</div><ul class="res-list">${resources}</ul>` : ""}
            ${brief}
          </div>
        </div>
      </li>`;
  }

  /* ---------------------------- Progress ------------------------------- */
  let ringCircumference = 327;
  function initMeter() {
    const ring = $("#ring-fg");
    if (ring && ring.r && ring.r.baseVal) {
      ringCircumference = 2 * Math.PI * ring.r.baseVal.value;
      ring.style.strokeDasharray = String(ringCircumference);
      ring.style.strokeDashoffset = String(ringCircumference);
    }
  }

  function updateProgress() {
    const steps = $$(".stop:not(.stop--origin)");
    const total = steps.length;
    const done = steps.filter((s) => s.classList.contains("is-done")).length;
    const pct = total ? Math.round((done / total) * 100) : 0;
    $("#progress-pct").textContent = `${pct}%`;
    $("#progress-done").textContent = done;
    $("#progress-total").textContent = total;
    const ring = $("#ring-fg");
    if (ring) ring.style.strokeDashoffset = String(ringCircumference - (pct / 100) * ringCircumference);
  }

  function saveProgress() {
    if (!state.progressKey) return;
    const done = $$(".stop:not(.stop--origin)").filter((s) => s.classList.contains("is-done")).map((s) => s.dataset.step);
    store.set(state.progressKey, JSON.stringify(done));
  }

  function loadProgress() {
    if (!state.progressKey) return;
    let done = [];
    try { done = JSON.parse(store.get(state.progressKey) || "[]"); } catch { done = []; }
    if (!Array.isArray(done)) done = [];
    $$(".stop:not(.stop--origin)").forEach((stopEl) => {
      if (done.includes(stopEl.dataset.step)) {
        stopEl.classList.add("is-done");
        const cb = $(".stop__check input", stopEl);
        if (cb) cb.checked = true;
      }
    });
    saveProgress(); // prune ids that no longer exist in this route
  }

  function bindRoadmapActions() {
    $("#reset-progress").onclick = () => {
      if (state.progressKey) store.remove(state.progressKey);
      $$(".stop:not(.stop--origin)").forEach((s) => { s.classList.remove("is-done"); const cb = $(".stop__check input", s); if (cb) cb.checked = false; });
      updateProgress();
    };
    $("#print-btn").onclick = () => window.print();
    $("#restart-btn").onclick = () => scrollToEl("#build");
  }

  /* ---------------------------- Init ----------------------------------- */
  function init() {
    try { initTheme(); } catch { /* never let theme block the app */ }
    $("#generate-btn").addEventListener("click", generateRoadmap);
    loadConfig().catch((err) => showConfigError(`Couldn't initialize the pathfinder — is the server running? (${err.message})`));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
