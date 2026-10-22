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
    const updateContact = () => {
      const selected = form.querySelector('[name=contact_method]:checked')?.value;
      form.querySelectorAll('[data-contact]').forEach(field => {
        field.hidden = !!selected && field.dataset.contact !== selected;
        field.querySelector('input').required = field.dataset.contact === selected;
      });
    };
    form.querySelectorAll('[name=contact_method]').forEach(input => input.addEventListener('change', updateContact));
    updateContact();
    const errors = document.getElementById('form-errors');
    if (errors) window.addEventListener('pageshow', () => requestAnimationFrame(() => errors.focus()));
    errors?.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
      const target = document.getElementById(link.hash.slice(1));
      (target?.matches('fieldset') ? target.querySelector('input') : target)?.focus();
    }));
    const datePlan = form.querySelector('[name=date_flexibility]');
    const dateInput = form.querySelector('[name=preferred_date]');
    const updateDate = () => { dateInput.required = datePlan.value === 'Preferred date'; };
    datePlan.addEventListener('change', updateDate);
    updateDate();
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
