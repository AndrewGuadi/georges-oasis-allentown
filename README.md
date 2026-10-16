# George’s Oasis Allentown

An existing Flask website extended with the restaurant, ice cream, mini golf, gatherings, specials, story, gallery, ordering and visit journeys described in the Astra specification.

## Run locally

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/flask --app app db upgrade
.venv/bin/flask --app app check-content
.venv/bin/flask --app app run
```

Compiled CSS is included. After changing Tailwind classes:

```bash
npm ci
npm run build:css
```

Run verification with `.venv/bin/python -m unittest discover -s tests`.

## Content and owner tools

Open `/admin` using the existing local demo credentials (`username` / `password`). The dashboard contains approved dated offers, saved event inquiries and one consolidated content-review screen. `/admin/preview/food` shows the full draft menu for owner review.

Business/menu/schedule content lives in `georges_oasis/content/site.json`. Only approved active records publish as current prices, schedules or offers. The public menu uses ordering/contact fallbacks until its records are approved. Review sources and update metadata before approval; run `check-content` and inspect previews afterward. Providers remain centralized in `georges_oasis/external_links.py`.

Event inquiries are saved before a receipt is shown. They do not confirm bookings. Duplicate submission tokens produce one record. Email is optional; unconfigured/failed delivery is visible in the staff inbox and dashboard. Never use a production deployment without a staff monitoring process.

For production set `OASIS_ENV=production`, `OWNER_USERNAME` and `OWNER_PASSWORD_HASH`; production refuses the demo password fallback. Optional notifications use `INQUIRY_RECIPIENT`, `INQUIRY_SENDER`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_TLS`, `SMTP_USERNAME` and `SMTP_PASSWORD`. No live notifications were sent during this build.

See [implementation and deployment notes](build_docs/IMPLEMENTATION.md) for the route map, components, schema, time semantics, verification and limitations. See [the consolidated owner review](build_docs/OWNER_REVIEW.md) for remaining business facts and source gaps.

## Production launch

Install `requirements.txt`, then set the following in your host's secret/environment settings:

- `OASIS_ENV=production`
- `OWNER_USERNAME`: a staff username other than the development default
- `OWNER_PASSWORD_HASH`: a Werkzeug hash of a strong, unique password
- `TRUSTED_HOSTS`: comma-separated host names, for example `georgesoasis.com,www.georgesoasis.com`
- `SECRET_KEY`: a stable random secret (or persist the automatically generated `instance/session-key`)
- Optional `DATABASE_URL`; the default database is `instance/oasis.sqlite`.

Generate a password hash without putting the password in shell history:

```bash
.venv/bin/python -c 'from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass("Owner password: ")))'
```

Back up `instance/`, run migrations and content validation, then start the production server:

```bash
.venv/bin/flask --app app db upgrade
.venv/bin/flask --app app check-content
.venv/bin/gunicorn --config gunicorn.conf.py app:app
```

Terminate HTTPS at your hosting proxy, redirect HTTP to HTTPS, and proxy to the configured `BIND` address. Set `FORWARDED_ALLOW_IPS` only to your trusted proxy addresses. Configure your proxy to preserve the approved public Host. Do not expose the Flask development server. Client-IP forwarding is deliberately not assumed: deploy the proxy's per-client login/submission rate limit as well, since the application may see the proxy as a shared client. Persist and back up the database, session key and uploads together; test restoring them before launch. Apply a retention policy agreed with the owner to inquiry data and backups.

Staff sign-in attempts are limited to ten per client address per 15 minutes across workers. Owner sessions expire after eight hours. Public error pages, security response headers, social sharing metadata and optimized image derivatives are included. Active homepage offers appear inline, without opening a modal.

The public menu uses the ordering service until the owner approves its draft records. Do not mark unverified prices/hours approved just to complete deployment. Confirm provider ordering/reservation behavior and establish who monitors the inquiry inbox before opening the site to customers.

Optional browser verification (requires Playwright and Chromium): `python scripts/browser_check.py`, with the local app on port 5000. It checks all public routes at 320, 390, 768 and 1440 pixels, plus mobile navigation and form errors. Screenshots and results go to `/tmp/oasis-browser`.
