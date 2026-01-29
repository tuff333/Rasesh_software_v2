// Global helpers for all pages
console.log('Rasesh IM PDF CRM loaded');

(function () {
  const body = document.getElementById('appBody');
  const btn  = document.getElementById('themeToggle');
  if (!body || !btn) return;

  // Load saved theme
  const saved = localStorage.getItem('rasesh_theme') || 'light';
  if (saved === 'dark') {
    body.classList.add('dark-mode');
    btn.innerHTML = '<i class="bi bi-sun"></i> Light';
  }

  btn.addEventListener('click', () => {
    const isDark = body.classList.toggle('dark-mode');
    localStorage.setItem('rasesh_theme', isDark ? 'dark' : 'light');
    btn.innerHTML = isDark
      ? '<i class="bi bi-sun"></i> Light'
      : '<i class="bi bi-moon"></i> Dark';
  });
})();
