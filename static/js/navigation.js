(() => {
  const header = document.getElementById('site-header');
  const mobileMenu = document.getElementById('mobile-navigation');
  if (!header || !mobileMenu) return;
  const toggle = mobileMenu.querySelector('summary');
  const desktop = window.matchMedia('(min-width: 1024px)');
  const updateHeader = () => header.classList.toggle('is-scrolled', window.scrollY > 0);
  const closeMenu = (restoreFocus = false) => {
    if (!mobileMenu.open) return;
    mobileMenu.open = false;
    if (restoreFocus) toggle.focus();
  };

  // Stay compact while scrolling in either direction; expand only at the top.
  window.addEventListener('scroll', updateHeader, { passive: true });
  window.addEventListener('pageshow', updateHeader);
  updateHeader();
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeMenu(true);
  });
  document.addEventListener('click', event => {
    if (!mobileMenu.contains(event.target)) closeMenu();
  });
  document.addEventListener('focusin', event => {
    if (!mobileMenu.contains(event.target)) closeMenu();
  });
  mobileMenu.addEventListener('click', event => {
    if (event.target.closest('a')) closeMenu();
  });
  desktop.addEventListener('change', () => closeMenu());
})();
