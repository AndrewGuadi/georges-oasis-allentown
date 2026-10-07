(() => {
  const header = document.getElementById('site-header');
  const mobileMenu = document.getElementById('mobile-navigation');
  const hoursMenu = document.getElementById('hours-menu');
  if (!header || !mobileMenu || !hoursMenu) return;
  const menus = [mobileMenu, hoursMenu];
  const desktop = window.matchMedia('(min-width: 1200px)');
  const closeMenu = (menu, restoreFocus = false) => {
    if (!menu.open) return;
    menu.open = false;
    if (restoreFocus) menu.querySelector('summary').focus();
  };
  const updateHeader = () => header.classList.toggle('is-scrolled', window.scrollY > 0);
  window.addEventListener('scroll', updateHeader, { passive: true });
  window.addEventListener('pageshow', updateHeader);
  updateHeader();
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') menus.forEach(menu => closeMenu(menu, menu.contains(document.activeElement)));
  });
  for (const type of ['click', 'focusin']) {
    document.addEventListener(type, event => menus.forEach(menu => {
      if (!menu.contains(event.target)) closeMenu(menu);
    }));
  }
  menus.forEach(menu => {
    menu.addEventListener('toggle', () => {
      if (menu.open) menus.filter(other => other !== menu).forEach(other => closeMenu(other));
    });
    menu.addEventListener('click', event => {
      if (event.target.closest('a')) closeMenu(menu, true);
    });
  });
  desktop.addEventListener('change', () => menus.forEach(menu => closeMenu(menu)));
})();
