(() => {
  const trigger = document.getElementById('today-special-trigger');
  const dialog = document.getElementById('today-special-dialog');
  if (!trigger || typeof dialog?.showModal !== 'function') return;

  const storageKey = 'oasis-today-special-seen';
  const date = dialog.dataset.date;
  const expires = Number(dialog.dataset.expires);
  let opener;
  let timer;

  function open(source) {
    if (Date.now() >= expires) {
      trigger.hidden = true;
      return;
    }
    if (document.querySelector('dialog[open]')) return;
    opener = source;
    dialog.showModal();
    try {
      window.localStorage.setItem(storageKey, date);
    } catch {
      // The button remains available when browser storage is disabled.
    }
  }

  function showAutomatically() {
    if (document.hidden || window.location.hash || window.scrollY >= window.innerHeight) return;
    if (document.activeElement !== document.body) return;
    try {
      if (window.localStorage.getItem(storageKey) === date) return;
    } catch {
      return;
    }
    open(trigger);
  }

  function schedule() {
    window.clearTimeout(timer);
    trigger.hidden = Date.now() >= expires;
    if (!trigger.hidden && !document.hidden) {
      timer = window.setTimeout(showAutomatically, 8000);
    }
  }

  trigger.addEventListener('click', () => open(trigger));
  dialog.addEventListener('close', () => opener?.focus({ preventScroll: true }));
  document.addEventListener('visibilitychange', schedule);
  window.addEventListener('pageshow', schedule);
  schedule();
})();
