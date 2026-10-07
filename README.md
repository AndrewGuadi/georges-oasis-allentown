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
