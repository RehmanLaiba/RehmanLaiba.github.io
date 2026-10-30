// Light/dark mode switch.
// Loaded in <head> (not deferred) so a saved choice applies before the page is drawn.
// Dark is the default: [data-theme="light"] in style.css overrides the colours.

(function () {
  var KEY = 'theme';
  var root = document.documentElement;

  try {
    var saved = localStorage.getItem(KEY);
    if (saved) root.dataset.theme = saved;
  } catch (e) {}

  function updateLabel(button) {
    var isLight = root.dataset.theme === 'light';
    button.setAttribute('aria-label', isLight ? 'Switch to dark mode' : 'Switch to light mode');
  }

  document.addEventListener('DOMContentLoaded', function () {
    var button = document.querySelector('.theme-toggle');
    if (!button) return;
    updateLabel(button);

    button.addEventListener('click', function () {
      var next = root.dataset.theme === 'light' ? 'dark' : 'light';
      root.dataset.theme = next;
      try { localStorage.setItem(KEY, next); } catch (e) {}
      updateLabel(button);
    });
  });
})();
