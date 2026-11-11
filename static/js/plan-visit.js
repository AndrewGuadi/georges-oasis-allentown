(() => {
  const trigger = document.getElementById('plan-visit-trigger');
  const dialog = document.getElementById('plan-visit-dialog');
  if (!trigger || typeof dialog?.showModal !== 'function') return;

  trigger.setAttribute('aria-haspopup', 'dialog');
  trigger.setAttribute('aria-controls', dialog.id);
  trigger.addEventListener('click', event => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    dialog.showModal();
  });
  dialog.addEventListener('close', () => trigger.focus());
})();
