/* Theme toggle. The no-flash bit runs inline in <head> (see base template);
   this only wires up the button and persists the choice. */
(function () {
  function systemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function current() {
    return document.documentElement.getAttribute("data-theme") || systemTheme();
  }
  function label(btn, theme) {
    var dark = theme === "dark";
    btn.textContent = dark ? "Light" : "Dark";
    btn.setAttribute("aria-pressed", String(dark));
    btn.setAttribute("aria-label", "Switch to " + (dark ? "light" : "dark") + " mode");
  }
  function set(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("theme", theme); } catch (e) {}
    var btn = document.getElementById("theme-toggle");
    if (btn) label(btn, theme);
  }

  function init() {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    label(btn, current());
    btn.addEventListener("click", function () {
      set(current() === "dark" ? "light" : "dark");
    });
  }

  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);
})();
