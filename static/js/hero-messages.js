(() => {
  const messages = document.getElementById('hero-messages');
  const toggle = document.getElementById('hero-messages-toggle');
  if (!toggle || typeof messages?.animate !== 'function') return;

  const slides = [...messages.querySelectorAll('[data-hero-slide]')];
  const slideCount = messages.querySelectorAll('h1 [data-hero-slide]').length;
  if (slideCount < 2) return;

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const readingTime = 5500;
  let currentSlide = 0;
  let paused = false;
  let timer;
  let animation;

  function showSlide(index) {
    currentSlide = index;
    for (const slide of slides) {
      slide.toggleAttribute('data-active', Number(slide.dataset.heroSlide) === index);
    }
  }

  function stop() {
    window.clearTimeout(timer);
    animation?.cancel();
    animation = undefined;
  }

  function animate(keyframes, duration, onFinish) {
    const running = messages.animate(keyframes, { duration, easing: 'ease-in-out', fill: 'both' });
    animation = running;
    running.onfinish = () => {
      if (animation !== running) return;
      running.cancel();
      animation = undefined;
      onFinish();
    };
  }

  function advance() {
    animate([
      { opacity: 1, transform: 'translateX(0)', filter: 'blur(0)' },
      { opacity: 0, transform: 'translateX(-24px)', filter: 'blur(7px)' },
    ], 190, () => {
      showSlide((currentSlide + 1) % slideCount);
      animate([
        { opacity: 0, transform: 'translateX(18px)', filter: 'blur(5px)' },
        { opacity: 1, transform: 'translateX(0)', filter: 'blur(0)' },
      ], 220, schedule);
    });
  }

  function schedule() {
    if (paused || reducedMotion.matches || document.hidden) return;
    timer = window.setTimeout(advance, readingTime);
  }

  function syncMotionPreference() {
    stop();
    const reduce = reducedMotion.matches;
    messages.toggleAttribute('data-rotating', !reduce);
    toggle.hidden = reduce;
    if (reduce) showSlide(0);
    schedule();
  }

  toggle.addEventListener('click', () => {
    paused = !paused;
    toggle.textContent = paused ? 'Play messages' : 'Pause messages';
    stop();
    schedule();
  });
  document.addEventListener('visibilitychange', () => {
    stop();
    schedule();
  });
  reducedMotion.addEventListener('change', syncMotionPreference);
  syncMotionPreference();
})();
