/** Theme: light | neon — persisted in localStorage. */

const KEY = "fsa_theme";

export function getStoredTheme() {
  try {
    const t = localStorage.getItem(KEY);
    if (t === "neon" || t === "light") return t;
  } catch {
    /* ignore */
  }
  return "light";
}

export function applyTheme(theme) {
  const t = theme === "neon" ? "neon" : "light";
  document.documentElement.setAttribute("data-theme", t);
  try {
    localStorage.setItem(KEY, t);
  } catch {
    /* ignore */
  }
  return t;
}

export function toggleTheme() {
  const next = getStoredTheme() === "neon" ? "light" : "neon";
  return applyTheme(next);
}

export function initTheme() {
  return applyTheme(getStoredTheme());
}
