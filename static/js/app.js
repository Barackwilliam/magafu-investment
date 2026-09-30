(function () {
  "use strict";
  var doc = document, body = doc.body, root = doc.documentElement;
  var desktop = window.matchMedia("(min-width: 900px)");
  function $(s, el) { return (el || doc).querySelector(s); }
  function $$(s, el) { return Array.prototype.slice.call((el || doc).querySelectorAll(s)); }

  /* ---------- Menyu ya pembeni (drawer) ---------- */
  var sidebar = $("#sidebar"), scrim = $(".scrim"), sheet = $("#sheet");
  function lock(on) { body.classList.toggle("locked", on); }
  function openMenu() {
    if (!sidebar) return;
    closeSheet();
    sidebar.classList.add("open"); scrim.classList.add("show"); lock(true);
    $$("[data-menu]").forEach(function (b) { b.setAttribute("aria-expanded", "true"); });
    var active = $(".nav a.active", sidebar);
    if (active) active.scrollIntoView({ block: "center" });
  }
  function closeMenu() {
    if (!sidebar) return;
    sidebar.classList.remove("open");
    if (!sheet || !sheet.classList.contains("open")) { scrim.classList.remove("show"); lock(false); }
    $$("[data-menu]").forEach(function (b) { b.setAttribute("aria-expanded", "false"); });
  }
  function openSheet() {
    if (!sheet) return;
    closeMenu();
    sheet.classList.add("open"); scrim.classList.add("show"); lock(true);
    sheet.setAttribute("aria-hidden", "false");
    var first = $("a", sheet); if (first) first.focus({ preventScroll: true });
  }
  function closeSheet() {
    if (!sheet || !sheet.classList.contains("open")) return;
    sheet.classList.remove("open"); sheet.setAttribute("aria-hidden", "true");
    if (!sidebar || !sidebar.classList.contains("open")) { scrim.classList.remove("show"); lock(false); }
  }
  $$("[data-menu]").forEach(function (b) { b.addEventListener("click", openMenu); });
  $$("[data-close]").forEach(function (b) { b.addEventListener("click", closeMenu); });
  $$("[data-sheet]").forEach(function (b) { b.addEventListener("click", function () {
    sheet && sheet.classList.contains("open") ? closeSheet() : openSheet(); }); });
  if (scrim) scrim.addEventListener("click", function () { closeMenu(); closeSheet(); });
  desktop.addEventListener("change", function (e) { if (e.matches) closeMenu(); });
  if (sidebar) $$("a", sidebar).forEach(function (a) {
    a.addEventListener("click", function () { if (!desktop.matches) closeMenu(); });
  });

  // Swipe: vuta kutoka ukingo wa kushoto kufungua menyu, kushoto kuifunga, chini kufunga sheet
  var sx = null, sy = null;
  doc.addEventListener("touchstart", function (e) { var t = e.touches[0]; sx = t.clientX; sy = t.clientY; }, { passive: true });
  doc.addEventListener("touchend", function (e) {
    if (sx === null || desktop.matches) return;
    var t = e.changedTouches[0], dx = t.clientX - sx, dy = t.clientY - sy;
    if (Math.abs(dy) < 60) {
      if (sidebar && !sidebar.classList.contains("open") && sx < 24 && dx > 70) openMenu();
      else if (sidebar && sidebar.classList.contains("open") && dx < -70) closeMenu();
    } else if (dy > 80 && sheet && sheet.classList.contains("open") && Math.abs(dx) < 60) closeSheet();
    sx = null;
  }, { passive: true });

  /* ---------- Menyu ya mtumiaji ---------- */
  $$("[data-popmenu]").forEach(function (menu) {
    var btn = $("button", menu);
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = !menu.classList.contains("open");
      $$(".menu.open").forEach(function (m) { m.classList.remove("open"); });
      menu.classList.toggle("open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });
  doc.addEventListener("click", function (e) {
    $$(".menu.open").forEach(function (m) { if (!m.contains(e.target)) m.classList.remove("open"); });
  });

  doc.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { closeMenu(); closeSheet(); $$(".menu.open").forEach(function (m) { m.classList.remove("open"); }); }
    // "/" au Ctrl+K: tafuta
    var tag = (e.target.tagName || "").toLowerCase();
    if ((e.key === "/" && tag !== "input" && tag !== "textarea" && tag !== "select") || ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k")) {
      var s = $("#global-search");
      if (s && s.offsetParent !== null) { e.preventDefault(); s.focus(); s.select(); }
      else if (!desktop.matches) { var l = $("[data-search-link]"); if (l) { e.preventDefault(); l.click(); } }
    }
  });

  /* ---------- Mwanga / giza ---------- */
  function setTheme(t) {
    root.setAttribute("data-theme", t);
    try { localStorage.setItem("magafu-theme", t); } catch (err) { /* private mode */ }
    var meta = $('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", t === "dark" ? "#09090A" : "#F5F3EE");
    doc.dispatchEvent(new CustomEvent("themechange", { detail: t }));
  }
  $$("[data-theme-toggle]").forEach(function (b) {
    b.addEventListener("click", function () { setTheme(root.getAttribute("data-theme") === "dark" ? "light" : "dark"); });
  });

  /* ---------- Toasts ---------- */
  $$(".toast").forEach(function (t, i) {
    function hide() { t.classList.add("out"); setTimeout(function () { t.remove(); }, 260); }
    // Gusa popote kwenye ujumbe kuufunga; makosa yanakaa muda mrefu zaidi ili yasomwe
    t.addEventListener("click", hide);
    setTimeout(hide, (t.classList.contains("toast-error") ? 9000 : 5200) + i * 400);
  });

  /* ---------- Jedwali linakuwa kadi kwenye simu ---------- */
  $$(".table-wrap table").forEach(function (table) {
    if (table.classList.contains("no-stack")) return;
    var heads = $$("thead th", table);
    if (!heads.length) return;
    table.classList.add("stack");
    var labels = heads.map(function (th) { return th.textContent.trim(); });
    $$("tbody tr, tfoot tr", table).forEach(function (tr) {
      var i = 0;
      Array.prototype.forEach.call(tr.children, function (td) {
        if (!td.hasAttribute("data-label")) td.setAttribute("data-label", labels[i] || "");
        i += parseInt(td.getAttribute("colspan") || "1", 10);
      });
    });
  });

  /* ---------- Filters zinajikunja kwenye simu ---------- */
  $$(".filters.collapsible").forEach(function (f) {
    var t = $("[data-filters-toggle]", f);
    if (!t) return;
    // Zikiwa zimetumika, zionekane wazi
    if (/[?&](q|jinsia|tawi|aina|njia|status|kuanzia|mpaka)=[^&]/.test(location.search)) f.classList.add("open");
    t.addEventListener("click", function () { f.classList.toggle("open"); });
  });

  /* ---------- Tabs: iliyochaguliwa ionekane ---------- */
  var onTab = $(".tabs a.on");
  if (onTab && onTab.parentElement.scrollWidth > onTab.parentElement.clientWidth) {
    onTab.parentElement.scrollLeft = onTab.offsetLeft - onTab.parentElement.clientWidth / 2 + onTab.clientWidth / 2;
  }

  /* ---------- Fomu: uthibitisho, kuzuia kutuma mara mbili ---------- */
  $$("form").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      var msg = f.getAttribute("data-confirm");
      if (msg && !window.confirm(msg)) { e.preventDefault(); return; }
      // getAttribute: fomu ya malipo ina sehemu inayoitwa "method", inayoficha f.method
      if ((f.getAttribute("method") || "get").toLowerCase() !== "post") return;
      if (f.dataset.sent) { e.preventDefault(); return; }
      f.dataset.sent = "1";
      var btn = e.submitter || $("button[type=submit], button:not([type])", f);
      if (btn) { btn.classList.add("is-loading"); btn.setAttribute("aria-busy", "true"); }
      // Kama ukurasa haukubadilika (mf. download), rudisha kitufe
      setTimeout(function () { delete f.dataset.sent; if (btn) { btn.classList.remove("is-loading"); btn.removeAttribute("aria-busy"); } }, 8000);
    });
  });
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) $$("form").forEach(function (f) { delete f.dataset.sent; $$(".is-loading", f).forEach(function (b) { b.classList.remove("is-loading"); }); });
  });

  /* ---------- Onyesha nenosiri ---------- */
  $$(".pw").forEach(function (w) {
    var b = $("button", w), i = $("input", w);
    if (!b || !i) return;
    b.addEventListener("click", function () {
      var show = i.type === "password"; i.type = show ? "text" : "password";
      w.classList.toggle("show", show); b.setAttribute("aria-label", show ? "Ficha nenosiri" : "Onyesha nenosiri");
      i.focus();
    });
  });

  /* ---------- Kiasi cha haraka (malipo) ---------- */
  $$("[data-amount]").forEach(function (b) {
    b.addEventListener("click", function () {
      var input = doc.getElementById(b.getAttribute("data-target"));
      if (input) { input.value = b.getAttribute("data-amount"); input.dispatchEvent(new Event("input")); input.focus(); }
    });
  });

  /* ---------- Kitufe cha chini: nenda kwenye fomu ---------- */
  $$("[data-focus]").forEach(function (a) {
    a.addEventListener("click", function () {
      var el = doc.getElementById(a.getAttribute("data-focus"));
      if (el) setTimeout(function () { el.focus(); if (el.select) el.select(); }, 380);
    });
  });

  /* ---------- Chagua kwa kubonyeza safu nzima ---------- */
  $$("tr[data-href]").forEach(function (tr) {
    tr.style.cursor = "pointer";
    tr.addEventListener("click", function (e) {
      if (e.target.closest("a, button, form, input, select")) return;
      window.location = tr.getAttribute("data-href");
    });
  });
})();
