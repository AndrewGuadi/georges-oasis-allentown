(() => {
  const dialog = document.getElementById('special-flyer-viewer');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const image = dialog.querySelector('[data-flyer-image]');
  const caption = dialog.querySelector('#special-flyer-caption');
  const error = dialog.querySelector('[data-flyer-error]');
  let opener;
  document.querySelectorAll('[data-special-flyer]').forEach(link => {
    link.addEventListener('click', event => {
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      opener = link;
      error.hidden = true;
      caption.textContent = link.dataset.caption;
      image.alt = `${link.dataset.caption} flyer`;
      image.src = link.href;
      dialog.querySelector('[data-flyer-original]').href = link.href;
      dialog.showModal();
    });
  });
  image.addEventListener('load', () => { error.hidden = true; });
  image.addEventListener('error', () => { error.hidden = false; });
  dialog.querySelector('[data-flyer-close]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    const box = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) dialog.close();
  });
  dialog.addEventListener('close', () => opener?.focus({ preventScroll: true }));
})();
