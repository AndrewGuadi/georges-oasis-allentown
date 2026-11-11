(() => {
  const menuPdfTrigger = document.getElementById('menu-pdf-trigger');
  const menuPdfDialog = document.getElementById('printed-menus');
  if (menuPdfTrigger && typeof menuPdfDialog?.showModal === 'function') {
    menuPdfTrigger.addEventListener('click', () => menuPdfDialog.showModal());
    menuPdfDialog.addEventListener('close', () => menuPdfTrigger.focus({ preventScroll: true }));
    menuPdfTrigger.hidden = false;
  }

  const searchPanel = document.querySelector('[data-menu-search]');
  if (searchPanel) {
    searchPanel.hidden = false;
    const input = document.getElementById('menu-search');
    const rows = [...document.querySelectorAll('[data-menu-item]')];
    const status = document.getElementById('menu-search-result');
    const filter = () => {
      const query = input.value.trim().toLocaleLowerCase();
      let count = 0;
      rows.forEach(row => { row.hidden = !row.dataset.search.includes(query); if (!row.hidden) count++; });
      document.querySelectorAll('.menu-category').forEach(category => {
        const items = [...category.querySelectorAll('[data-menu-item]')];
        category.hidden = !!query && !items.some(item => !item.hidden);
        category.querySelectorAll('.menu-group').forEach(heading => {
          let sibling = heading.nextElementSibling;
          let visible = false;
          while (sibling && !sibling.classList.contains('menu-group')) {
            if (sibling.matches('[data-menu-item]') && !sibling.hidden) visible = true;
            sibling = sibling.nextElementSibling;
          }
          heading.hidden = !visible;
          const groupPhotos = heading.nextElementSibling;
          if (groupPhotos?.matches('[data-menu-group-photos]')) groupPhotos.hidden = !visible;
        });
      });
      status.textContent = query ? count ? `${count} matching ${count === 1 ? 'dish' : 'dishes'}.` : 'No matching dishes. Clear the search to browse every category.' : '';
    };
    input.addEventListener('input', filter);
    document.getElementById('reset-menu').addEventListener('click', () => { input.value = ''; filter(); input.focus(); });
    document.querySelectorAll('.menu-sidebar nav a, .food-features a').forEach(link => link.addEventListener('click', () => { input.value = ''; filter(); }));
  }
  const form = document.getElementById('inquiry-form');
  if (form) {
    const errors = document.getElementById('form-errors');
    if (errors) window.addEventListener('pageshow', () => requestAnimationFrame(() => errors.focus()));
    errors?.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
      document.getElementById(link.hash.slice(1))?.focus();
    }));
    form.addEventListener('submit', () => {
      const button = form.querySelector('[type=submit]');
      button.disabled = true;
      button.textContent = 'Sending your request…';
    });
    window.addEventListener('pageshow', () => {
      const button = form.querySelector('[type=submit]');
      button.disabled = false;
      button.textContent = 'Send Event Inquiry →';
    });
  }
})();

