"""Run against a local preview: PLAYWRIGHT_BROWSERS_PATH=... python scripts/browser_check.py."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROUTES = ['/', '/food-and-ice-cream', '/ice-cream', '/mini-golf', '/gatherings', '/visit', '/specials', '/our-story', '/gallery', '/order']
artifacts = Path('/tmp/oasis-browser')
artifacts.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    results = []
    for width in [320, 390, 768, 1440]:
        page.set_viewport_size({'width': width, 'height': 900})
        for route in ROUTES:
            response = page.goto(os.environ.get('OASIS_TEST_BASE_URL', 'http://127.0.0.1:5000') + route, wait_until='networkidle')
            assert response.status == 200, (route, response.status)
            assert page.locator('h1').count() == 1, route
            overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth')
            assert not overflow, (route, width, 'horizontal overflow')
            page.locator('img').evaluate_all("images => images.forEach(i => i.loading = 'eager')")
            page.wait_for_function("() => Array.from(document.images).every(i => i.complete)")
            page.locator('img').evaluate_all("images => Promise.all(images.map(i => i.decode().catch(() => {})))")
            broken = page.locator('img').evaluate_all('(images) => images.filter(i => i.complete && !i.naturalWidth).map(i => i.src)')
            assert not broken, (route, broken)
            results.append({'route': route, 'width': width, 'ok': True})
            if width in [390, 1440]:
                page.screenshot(path=str(artifacts / f'{route.strip("/") or "home"}-{width}.png'), full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.goto(os.environ.get('OASIS_TEST_BASE_URL', 'http://127.0.0.1:5000') + '/')
    page.locator('#mobile-navigation summary').click()
    assert page.locator('#mobile-navigation').get_attribute('open') is not None
    page.keyboard.press('Escape')
    assert page.locator('#mobile-navigation').get_attribute('open') is None
    page.goto(os.environ.get('OASIS_TEST_BASE_URL', 'http://127.0.0.1:5000') + '/gatherings')
    assert page.locator('#phone').is_visible()
    assert page.locator('#email').is_visible()
    page.locator('button[type=submit]').click()
    assert page.locator('#form-errors').is_visible()
    expect(page.locator('#form-errors')).to_be_focused()
    assert not errors, errors
    browser.close()
    (artifacts / 'results.json').write_text(json.dumps(results, indent=2))
    print(f'{len(results)} page/viewport checks passed; navigation and form validation passed. Screenshots: {artifacts}')
