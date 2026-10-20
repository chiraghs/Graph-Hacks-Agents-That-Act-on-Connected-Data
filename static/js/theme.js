// TwinForge Connected Graph - Theme Controller
const THEME_KEY = "twinforge-connected-graph-theme";

function updateThemeUI(theme) {
  const sunIcon = document.getElementById('theme-sun-icon');
  const moonIcon = document.getElementById('theme-moon-icon');
  const btn = document.getElementById('btn-theme-toggle');
  if (theme === 'light') {
    if (sunIcon) sunIcon.classList.remove('hidden');
    if (moonIcon) moonIcon.classList.add('hidden');
    if (btn) btn.title = "Switch to dark theme";
  } else {
    if (sunIcon) sunIcon.classList.add('hidden');
    if (moonIcon) moonIcon.classList.remove('hidden');
    if (btn) btn.title = "Switch to light theme";
  }
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch (e) {}
  updateThemeUI(next);
}
