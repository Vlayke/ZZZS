// Apply before styles load so a saved dark preference never flashes light.
(() => {
  const key = 'zzzs-theme';
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  const valid = value => ['system', 'light', 'dark'].includes(value);
  let preference = 'system';
  try {
    const saved = localStorage.getItem(key);
    if (valid(saved)) preference = saved;
  } catch { /* The theme also works when browser storage is unavailable. */ }
  function apply() {
    document.documentElement.dataset.theme = preference === 'system' ? (media.matches ? 'dark' : 'light') : preference;
  }
  apply();
  media.addEventListener('change', apply);
  document.addEventListener('DOMContentLoaded', () => {
    const select = document.getElementById('theme');
    select.value = preference;
    select.addEventListener('change', () => {
      preference = valid(select.value) ? select.value : 'system';
      try { localStorage.setItem(key, preference); } catch { /* Session-only preference. */ }
      apply();
    });
  });
})();
