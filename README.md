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

Compiled CSS is included. Rebuild it after editing Tailwind classes or any CSS imported by the homepage bundle:

```bash
npm ci
npm run build:css
```

Run verification with `.venv/bin/python -m unittest discover -s tests`.

## Content and owner tools

Open `/admin` using the existing local demo credentials (`username` / `password`). The dashboard contains approved dated offers, saved event inquiries and one consolidated content-review screen. `/admin/preview/food` shows the full draft menu for owner review.

Business/menu/schedule content lives in `georges_oasis/content/site.json`. Only approved active records publish as current prices, schedules or offers. The public menu uses ordering/contact fallbacks until its records are approved. Review sources and update metadata before approval; run `check-content` and inspect previews afterward. Providers remain centralized in `georges_oasis/external_links.py`.

Event inquiries are saved before a receipt is shown. They do not confirm bookings. Duplicate submission tokens produce one record. Email is optional; unconfigured/failed delivery is visible in the staff inbox and dashboard. Never use a production deployment without a staff monitoring process.

For production set `OASIS_ENV=production`, `OWNER_USERNAME` and `OWNER_PASSWORD_HASH`; production refuses the demo password fallback. Optional notifications use `INQUIRY_RECIPIENT`, `INQUIRY_SENDER`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_TLS`, `SMTP_SSL`, `SMTP_USERNAME` and `SMTP_PASSWORD`.

### Email configuration and testing

For local development, copy the mail settings from `.env.example` into your ignored `.env` and restrict its permissions with `chmod 600 .env`. Both the Flask CLI and the `app:app` Gunicorn entry point load this file; existing environment variables take precedence. Restart running web and worker processes after changing mail settings.

For Gmail, use the full account email as `SMTP_USERNAME` and a current Google App Password as `SMTP_PASSWORD`. The sender should be that account or an authorized sending alias. Spaces in Google's four-group app password display are accepted. Use port 587 with `SMTP_TLS=true` and `SMTP_SSL=false`, or port 465 with `SMTP_SSL=true`. Both encrypted transports verify the server certificate.

Send one labeled test to the configured recipient:

```bash
.venv/bin/flask --app app test-email
```

Success means the SMTP server accepted the message; confirm it arrives in the recipient inbox or spam folder. The command creates no inquiry and does not drain existing queued notifications. Its errors omit credentials and provider message bodies.

Customer inquiries are committed to the database first, then the website independently attempts the staff alert and a customer acknowledgment when an email address is provided. Email failures do not fail the submission: the customer still receives their receipt, and staff can review both delivery statuses. Set `STAFF_BASE_URL` to the final website origin for direct staff inbox links.

On a hosted deployment, prefer the host's private environment-variable settings rather than uploading a local `.env` or typing credentials into shell `export` commands. No separate password manager is required. A `.env` remains plaintext and should stay out of Git, build artifacts and shared backups.

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

## Analytics, Search Console and inquiry spam protection

Set `GA4_MEASUREMENT_ID` to the property's web stream ID (`G-…`) to enable public-site analytics. In that web stream, disable the enhanced-measurement form interactions, outbound clicks, downloads, and browser-history page views so the site's explicit events supply those measurements. Use Realtime or DebugView to check a page view and the following events. Mark `generate_lead` as a key event and use a funnel exploration with device category to compare mobile and desktop.

| Event | What it measures |
| --- | --- |
| `oasis_action` | Clicks to important pages, calls, directions, ordering, reservations and menu PDFs |
| `inquiry_form_view`, `inquiry_form_start` | The form coming into view and the first interaction with it |
| `inquiry_submit_attempt`, `inquiry_submit_error` | Submissions and recoverable errors, with a fixed error reason |
| `generate_lead` | The first confirmation view after a new inquiry is saved |

Register `action`, `menu`, `form_name`, and `reason` as event-scoped custom dimensions as needed. The tag uses query-free page URLs, a generic receipt URL, and referrer origins. It sends no inquiry fields or reference identifiers. Browser tracking reflects visitors who can load the tag, while the staff inbox records saved inquiries.

For Google Search Console, add or select the Domain property `georgesoasis.com` and verify the Google-provided TXT record at the root of the Cloudflare DNS zone. Ensure the deployed WSGI app uses its production settings above. Confirm public pages have no `X-Robots-Tag: noindex` and that `/robots.txt` allows public crawling, then submit `https://www.georgesoasis.com/sitemap.xml`. Inspect the live homepage, menu and gatherings URLs after submission.

For Turnstile, create a Managed widget for `www.georgesoasis.com` with pre-clearance disabled. Set `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY` together in the web app's environment. The secret is server-only. The gatherings form verifies each new submission before saving or sending mail. Test both the success path and a rejected challenge after enabling the widget.


## Stage-two staff backend

Menu, weekly specials, dated offers, media and typed inquiry workflows are now available under `/admin`. The development login remains `username` / `password` until named accounts are provisioned; production rejects these defaults. The catalog imports the current menu, including price-free dishes and portions, and keeps unreviewed prices hidden.

On a deployment upgrading from the previous staff backend, apply the database migrations before reloading the web app. For a first catalog import, review `flask --app app import-catalog --dry-run`, then run `flask --app app import-catalog`. The import preserves the current public menu and refuses to replace an existing staff catalog.

No always-on notification worker is required. Each new inquiry saves its request, initial history and notification jobs before attempting email. Duplicate submissions return the original receipt without sending either email again. Missing configuration or delivery failures remain visible in the staff inbox; use **Retry staff notification** or **Retry customer acknowledgment** to retry only the affected email. Retrying one does not resend the successful other message.

To retry queued jobs that are due, run this command from the project directory:

```bash
.venv/bin/flask --app app process-notifications --limit 100
```

It processes up to 100 eligible jobs and exits. Failed deliveries retain their retry schedule, with at most five attempts before staff intervention is needed. `--watch` remains optional for deployments that choose continuous background retries. Staff should monitor the inquiry dashboard regardless of email delivery.

Staff alerts, customer acknowledgments and delivery-test emails share branded HTML templates under `templates/emails/`, with a plain-text alternative. They use the site’s green, cream and gold palette, a text wordmark, system fonts and a fluid table layout; no remote images or fonts are required. Staff alerts include a dashboard button when `STAFF_BASE_URL` is valid, or sign-in instructions when it is absent. Customer acknowledgments include the reference, next steps and booking disclaimer, with replies directed to the restaurant's public email (or the sender when that address is unavailable). They include no staff links or submitted message details. Phone-only inquiries receive the on-screen receipt. The receipt reflects customer email status without exposing the address. Render fixture previews without sending mail using `.venv/bin/python scripts/email_preview.py`.

Apply database migrations before deploying customer acknowledgments. Existing inquiries are marked `not_requested`; upgrading does not send historical customers any email.
