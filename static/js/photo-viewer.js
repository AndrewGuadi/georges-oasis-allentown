(() => {
  document.querySelectorAll('[data-photo-viewer]').forEach(dialog => {
    const photos = [...document.querySelectorAll(dialog.dataset.photoLinks)];
    if (!photos.length || typeof dialog.showModal !== 'function') return;
    const picture = dialog.querySelector('[data-viewer-image]');
    const caption = dialog.querySelector('[data-photo-caption]');
    const count = dialog.querySelector('[data-photo-count]');
    const error = dialog.querySelector('[data-photo-error]');
    const original = dialog.querySelector('[data-photo-original]');
    let index = 0;
    let opener;
    picture.addEventListener('load', () => { error.hidden = true; });
    picture.addEventListener('error', () => { error.hidden = false; });
    const show = next => {
      index = (next + photos.length) % photos.length;
      const link = photos[index];
      error.hidden = true;
      picture.loading = 'eager';
      picture.alt = link.querySelector('img').alt;
      picture.src = link.href;
      original.href = link.href;
      caption.textContent = link.dataset.caption;
      count.textContent = `${dialog.dataset.photoLabel} ${index + 1} of ${photos.length}`;
    };
    photos.forEach((link, position) => link.addEventListener('click', event => {
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      opener = link;
      show(position);
      dialog.showModal();
    }));
    dialog.querySelector('[data-photo-close]').addEventListener('click', () => dialog.close());
    dialog.querySelector('[data-photo-prev]').addEventListener('click', () => show(index - 1));
    dialog.querySelector('[data-photo-next]').addEventListener('click', () => show(index + 1));
    dialog.addEventListener('keydown', event => {
      if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
        event.preventDefault();
        show(index + (event.key === 'ArrowRight' ? 1 : -1));
      }
    });
    dialog.addEventListener('click', event => {
      const box = dialog.getBoundingClientRect();
      if (event.target === dialog && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) dialog.close();
    });
    dialog.addEventListener('close', () => opener?.focus({ preventScroll: true }));
    if (photos.length === 1) dialog.querySelectorAll('[data-photo-prev],[data-photo-next]').forEach(button => { button.hidden = true; });
  });
})();
