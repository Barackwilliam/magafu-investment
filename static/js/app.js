(function () {
  var body = document.body;
  var sidebar = document.getElementById("sidebar");
  var scrim = document.querySelector(".scrim");
  var toggle = document.querySelector("[data-menu]");
  var mobile = window.matchMedia("(max-width: 860px)");

  function openMenu() {
    sidebar.classList.add("open"); scrim.classList.add("show"); body.classList.add("menu-open");
    if (toggle) toggle.setAttribute("aria-expanded", "true");
    var active = sidebar.querySelector(".sub a.active, .main-link.active");
    if (active) active.scrollIntoView({ block: "center" });
  }
  function closeMenu() {
    sidebar.classList.remove("open"); scrim.classList.remove("show"); body.classList.remove("menu-open");
    if (toggle) { toggle.setAttribute("aria-expanded", "false"); }
  }
  if (toggle) toggle.addEventListener("click", openMenu);
  if (scrim) scrim.addEventListener("click", closeMenu);
  document.querySelectorAll("[data-close]").forEach(function (b) { b.addEventListener("click", closeMenu); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeMenu(); });
  // Ukibonyeza link kwenye simu, menyu inajifunga
  sidebar.querySelectorAll("a").forEach(function (a) {
    a.addEventListener("click", function () { if (mobile.matches) closeMenu(); });
  });
  mobile.addEventListener("change", function (e) { if (!e.matches) closeMenu(); });

  // Swipe: vuta kutoka ukingo wa kushoto kufungua, vuta kushoto kufunga
  var startX = null, startY = null;
  document.addEventListener("touchstart", function (e) {
    var t = e.touches[0]; startX = t.clientX; startY = t.clientY;
  }, { passive: true });
  document.addEventListener("touchend", function (e) {
    if (startX === null || !mobile.matches) return;
    var t = e.changedTouches[0], dx = t.clientX - startX, dy = Math.abs(t.clientY - startY);
    if (dy < 60) {
      if (!sidebar.classList.contains("open") && startX < 24 && dx > 60) openMenu();
      else if (sidebar.classList.contains("open") && dx < -60) closeMenu();
    }
    startX = null;
  }, { passive: true });

  // Tables zinageuka kadi kwenye simu: kila seli inapata jina la safu yake
  document.querySelectorAll(".table-wrap table").forEach(function (table) {
    var heads = table.querySelectorAll("thead th");
    if (!heads.length) return;
    table.classList.add("stack");
    var labels = Array.prototype.map.call(heads, function (th) { return th.textContent.trim(); });
    table.querySelectorAll("tbody tr, tfoot tr").forEach(function (tr) {
      var i = 0;
      Array.prototype.forEach.call(tr.children, function (td) {
        if (!td.hasAttribute("data-label")) td.setAttribute("data-label", labels[i] || "");
        i += parseInt(td.getAttribute("colspan") || "1", 10);
      });
    });
  });

  // Tab iliyochaguliwa ionekane kwenye simu
  var onTab = document.querySelector(".tabs a.on");
  if (onTab) onTab.scrollIntoView({ block: "nearest", inline: "center" });

  // Kitufe cha chini: nenda kwenye fomu na fungua keyboard
  document.querySelectorAll("[data-focus]").forEach(function (a) {
    a.addEventListener("click", function () {
      var el = document.getElementById(a.getAttribute("data-focus"));
      if (el) setTimeout(function () { el.focus(); el.select && el.select(); }, 350);
    });
  });

  // Uthibitisho kabla ya vitendo muhimu
  document.querySelectorAll("form[data-confirm]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (!window.confirm(f.getAttribute("data-confirm"))) e.preventDefault();
    });
  });
})();
