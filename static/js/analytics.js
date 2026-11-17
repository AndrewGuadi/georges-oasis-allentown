(() => {
  const script = document.currentScript;
  const { analyticsId, inquiryResult } = script.dataset;
  const { origin, pathname } = window.location;
  const isReceipt = pathname.startsWith('/inquiry-received/');
  const pageLocation = origin + (isReceipt ? '/inquiry-received' : pathname);
  const pageReferrer = document.referrer ? new URL(document.referrer).origin : '';

  window.dataLayer = window.dataLayer || [];
  function tag() {
    window.dataLayer.push(arguments);
  }
  tag('js', new Date());
  tag('config', analyticsId, {
    send_page_view: false,
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
    page_location: pageLocation,
    page_referrer: pageReferrer,
  });

  const send = (name, details = {}) => tag('event', name, {
    page_location: pageLocation,
    page_referrer: pageReferrer,
    ...details,
  });
  if (!inquiryResult || isReceipt) {
    send('page_view');
  }
  const form = document.getElementById('inquiry-form');
  if (inquiryResult === 'saved') {
    send('generate_lead', { form_name: 'gatherings' });
  } else if (inquiryResult) {
    send('inquiry_submit_error', { form_name: 'gatherings', reason: inquiryResult });
  }
  if (form) {
    let viewed = Boolean(inquiryResult);
    let started = viewed;
    const view = () => {
      if (viewed) return;
      viewed = true;
      send('inquiry_form_view', { form_name: 'gatherings' });
    };
    const start = () => {
      view();
      if (started) return;
      started = true;
      send('inquiry_form_start', { form_name: 'gatherings' });
    };
    if (!viewed && 'IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          view();
          observer.disconnect();
        }
      }, { threshold: 0.1 });
      observer.observe(form);
    }
    form.addEventListener('focusin', (event) => {
      if (event.target.matches('input:not([type=hidden]):not(#website), select, textarea')) start();
    });
    form.addEventListener('submit', () => {
      start();
      send('inquiry_submit_attempt', { form_name: 'gatherings' });
    });
  }

  const externalActions = new Set(['order-foodbooking', 'order-grubhub', 'reserve-google', 'group-reservation-inquiry']);
  const publicActions = new Map([
    ['/food-and-ice-cream', 'menu'],
    ['/ice-cream', 'ice_cream'],
    ['/mini-golf', 'mini_golf'],
    ['/gatherings', 'gatherings'],
    ['/order', 'order'],
    ['/visit', 'visit'],
  ]);
  const pdfActions = new Map([
    ['/static/menus/Breakfast_Menu.pdf', 'breakfast'],
    ['/static/menus/Lunch_and_Dinner_Menu.pdf', 'lunch_and_dinner'],
    ['/static/menus/Ice_Cream_and_Desserts_Menu.pdf', 'ice_cream_and_desserts'],
  ]);
  document.addEventListener('click', (event) => {
    const control = event.target.closest('a[href], #menu-pdf-trigger');
    if (!control) return;
    if (control.id === 'plan-visit-trigger' || control.id === 'menu-pdf-trigger') {
      send('oasis_action', { action: control.id === 'plan-visit-trigger' ? 'plan_your_visit' : 'open_pdf_menus' });
      return;
    }
    const target = new URL(control.href);
    const action = control.dataset.action;
    if (externalActions.has(action)) {
      send('oasis_action', { action });
    } else if (target.protocol === 'tel:') {
      send('oasis_action', { action: 'call_restaurant' });
    } else if (target.hostname === 'www.google.com' && target.pathname.startsWith('/maps/search')) {
      send('oasis_action', { action: 'get_directions' });
    } else if (target.origin === origin) {
      if (pdfActions.has(target.pathname)) {
        send('oasis_action', { action: 'open_menu_pdf', menu: pdfActions.get(target.pathname) });
      } else if (target.pathname === '/gatherings' && target.hash === '#event-inquiry') {
        send('oasis_action', { action: 'open_inquiry_form' });
      } else if (target.pathname !== pathname && publicActions.has(target.pathname)) {
        send('oasis_action', { action: publicActions.get(target.pathname) });
      }
    }
  });

  const startup = new AbortController();
  function loadTag() {
    if (startup.signal.aborted) return;
    startup.abort();
    const loader = document.createElement('script');
    loader.async = true;
    loader.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(analyticsId);
    document.head.append(loader);
  }

  if (script.hasAttribute('data-analytics-after-load') && !inquiryResult
      && document.readyState !== 'complete' && !document.hidden) {
    // The event queue is ready now. Let the hero load first unless a visitor acts.
    const options = { signal: startup.signal, capture: true };
    window.addEventListener('load', loadTag, { signal: startup.signal });
    for (const event of ['pointerdown', 'keydown', 'click']) {
      window.addEventListener(event, loadTag, options);
    }
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) loadTag();
    }, { signal: startup.signal });
  } else {
    loadTag();
  }
})();
