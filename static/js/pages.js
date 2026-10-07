(() => {
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
      status.textContent = query ? count ? `${count} matching ${count === 1 ? 'dish' : 'dishes'}.` : 'No matching dishes. Clear the search to browse every category.' : '';
    };
    input.addEventListener('input', filter);
    document.getElementById('reset-menu').addEventListener('click', () => { input.value = ''; filter(); input.focus(); });
  }
  const form = document.getElementById('inquiry-form');
  if (form) {
    const updateContact = () => {
      const selected = form.querySelector('[name=contact_method]:checked')?.value;
      form.querySelectorAll('[data-contact]').forEach(field => { field.hidden = selected && field.dataset.contact !== selected; });
    };
    form.querySelectorAll('[name=contact_method]').forEach(input => input.addEventListener('change', updateContact));
    updateContact();
    const errors = document.getElementById('form-errors');
    if (errors) errors.focus();
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
