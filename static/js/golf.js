(() => {
  const dialog = document.querySelector('.golf-lightbox');
  const photos = [...document.querySelectorAll('.golf-photo-open')];
  if (!dialog || !photos.length || !dialog.showModal) return;
  const picture = dialog.querySelector('img');
  const caption = dialog.querySelector('#golf-lightbox-caption');
  const count = dialog.querySelector('[data-photo-count]');
  let index = 0;
  let opener;
  const show = next => {
    index = (next + photos.length) % photos.length;
    picture.src = photos[index].href;
    picture.alt = photos[index].querySelector('img').alt;
    caption.textContent = photos[index].dataset.caption;
    count.textContent = `Course photo ${index + 1} of ${photos.length}`;
  };
  photos.forEach((link, i) => link.addEventListener('click', event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    opener = link;
    show(i);
    dialog.showModal();
  }));
  dialog.querySelector('[data-photo-close]').addEventListener('click', () => dialog.close());
  dialog.querySelector('[data-photo-prev]').addEventListener('click', () => show(index - 1));
  dialog.querySelector('[data-photo-next]').addEventListener('click', () => show(index + 1));
  dialog.addEventListener('keydown', event => {
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault(); show(index + (event.key === 'ArrowRight' ? 1 : -1));
    }
  });
  dialog.addEventListener('click', event => {
    const rect = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
  });
  dialog.addEventListener('close', () => opener?.focus());
  if (photos.length === 1) dialog.querySelectorAll('[data-photo-prev],[data-photo-next]').forEach(button => button.hidden = true);
})();
