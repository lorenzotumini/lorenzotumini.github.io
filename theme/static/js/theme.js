(() => {
  const root = document.documentElement;
  const toggle = document.querySelector(".theme-toggle");

  if (!toggle) {
    return;
  }

  const icon = toggle.querySelector("span");

  function isLight() {
    return root.dataset.theme === "light";
  }

  function updateToggle() {
    const nextTheme = isLight() ? "dark" : "light";
    const label = `Switch to ${nextTheme} mode`;

    toggle.setAttribute("aria-label", label);
    toggle.title = label;
    icon.textContent = isLight() ? "☾" : "☼";
  }

  toggle.hidden = false;
  updateToggle();

  toggle.addEventListener("click", () => {
    const nextTheme = isLight() ? "dark" : "light";

    if (nextTheme === "light") {
      root.dataset.theme = "light";
    } else {
      delete root.dataset.theme;
    }

    try {
      localStorage.setItem("theme", nextTheme);
    } catch (_) {}

    updateToggle();
  });
})();
