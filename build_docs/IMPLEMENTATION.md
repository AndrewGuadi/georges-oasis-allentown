# George’s Oasis implementation handoff

## Delivered

The existing Flask application now has designed interior pages matching the homepage’s cream, forest-green, gold and palm system. The original hero photo and all homepage sections remain. Unsupported fixed Burger Night, hole-count and anniversary claims were replaced with evergreen copy in the same sections.

Public pages are server rendered. Interior pages share introduction, menu category, price row, service schedule, FAQ, photo card and final-action components. The header prioritizes the main experiences; secondary destinations use More on desktop and the mobile menu. Homepage ice-cream and group actions now reach their dedicated journeys. Maps, phone, ordering, delivery and table reservation remain working direct handoffs.

| Route | Purpose |
| --- | --- |
| `/` | Existing homepage composition |
| `/food-and-ice-cream` | Canonical restaurant menu; all approved structured categories |
| `/ice-cream` | Dedicated dessert and seasonal-availability page |
| `/mini-golf` | Course, rates/status, visit planning and group handoff |
| `/gatherings` | Event information and server-side inquiry form |
| `/visit` | Location, independent service hours, phone and reservations |
| `/specials` | Approved active dated and recurring offers; useful empty state |
| `/our-story` | Restaurant narrative and original photographs |
| `/gallery` | Categorized original photographs and relevant next actions |
| `/order` | FoodBooking and Grubhub handoffs |
| `/inquiry-received/<reference>` | Session-authorized, no-index receipt with no contact details |
| `/admin/inquiries` | Authenticated staff inbox |
| `/admin/content-review` | Consolidated owner review and draft previews |
| `/admin/preview/<page-key>` | Authenticated, no-index draft rendering |
| `/sitemap.xml`, `/robots.txt` | Canonical discovery and private-route exclusions |

Permanent redirects preserve query strings: `/menus.html` and `/menu` → `/food-and-ice-cream`; `/hours--info.html` → `/visit`; `/mini-golf.html` → `/mini-golf`; `/specials.html` → `/specials`; `/gallery.html` → `/gallery`; `/private-eventscatering.html` and `/parties` → `/gatherings`; `/index.html` → `/`.

## Data and behavior

- `georges_oasis/content/site.json`: versioned profile, 176 draft menu records, observed schedules, draft recurring specials, rates, story and media review notes.
- `georges_oasis/content.py`: publication, exact currency formatting, seasonal state, exceptions and local-time schedule rules. `flask --app app check-content` validates editable records.
- `georges_oasis/external_links.py`: centralized provider and external destinations. Missing primary ordering/reservation configuration shows a phone fallback.
- `georges_oasis/inquiries.py`: validation, CSRF-compatible submission, honeypot, database-backed rate limits, unique submission tokens, durable storage and optional staff notification.
- `migrations/versions/1e8469c0a112_event_inquiries.py`: reversible inquiry/rate-limit tables and offer-approval metadata. Legacy offers previously enabled by the owner retain approved status.
- `templates/public/includes/components.html`: shared page and content components.
- `static/css/pages.css`: interior design. `static/css/tailwind.css` is compiled and committed; no Tailwind browser/CDN runtime is needed.

A saved inquiry is not a booking. Double-clicks/retries with the same token return one request and receipt. Notification failure preserves the saved request, records failure state, emits a reference-only operational log and alerts staff in the dashboard. No notification is attempted without an approved configured recipient or a test notifier. Form content is not put in URLs, analytics or diagnostic logs. Staff states are new/contacted/closed. Notification state is independent.

All business time uses America/New_York. Publication windows include the start and exclude the end. Weekly overnight windows are supported. During fall-back, opening uses the first clock occurrence and closing the second. A skipped spring clock time moves forward by the gap. The dated-offer editor rejects ambiguous or nonexistent clock times so staff choose an explicit unambiguous time. Date exceptions override the normal schedule; seasonal and temporary closures override it. Unknown schedules never produce an Open or Closed claim. Public time-sensitive pages require revalidation rather than being served from an immutable cache.

## Local setup and existing-host deployment

1. Install Python dependencies: `.venv/bin/pip install -r requirements.txt`.
2. Back up `instance/` before upgrading an existing installation. A pre-change local database backup was made at `/tmp/oasis-before-page-build.sqlite` during this work.
3. Run `.venv/bin/flask --app app db upgrade`. This was applied to the local workspace database.
4. Run `.venv/bin/flask --app app check-content`.
5. Run `npm ci` and `npm run build:css` when templates or Tailwind classes change. The generated stylesheet is included, so Node is not needed just to serve the application.
6. Run `.venv/bin/flask --app app run` for a local preview. Deploy using the existing Flask hosting process only after review; this work has not published the site or changed DNS/providers.

Production environment:

- `OASIS_ENV=production`: enables secure session cookies and refuses startup without `OWNER_PASSWORD_HASH`.
- `OWNER_USERNAME`, `OWNER_PASSWORD_HASH`: configure actual staff credentials; generate a Werkzeug password hash. Local development retains the existing demo login.
- `SECRET_KEY`: set a stable secret or persist `instance/session-key`.
- Optional email: `INQUIRY_RECIPIENT` (one approved address), `INQUIRY_SENDER`, `SMTP_HOST`, `SMTP_PORT` (587 default), `SMTP_TLS` (true default), `SMTP_USERNAME`, `SMTP_PASSWORD`.

Without SMTP configuration, inquiries still save to the authenticated inbox and are flagged for direct dashboard review. Staff must actively monitor this inbox. Confirm the owner’s retention policy before enabling deletion/automation; no automatic PII deletion or unapproved retention interval has been introduced. Back up the database and session key with uploads, restrict backup access, and remove records/backups according to the agreed policy. Verify the trusted proxy/client-address configuration if deploying behind a proxy; rate limiting uses the address presented to Flask and does not trust arbitrary forwarded headers.

## Verification and limits

The automated suite covers all canonical routes and internal anchors/assets, redirect query preservation, private review/receipt access, provider overrides/fallbacks, approved menu publication, offer timing, open/cutoff/close boundaries, overnight schedules, holidays, seasonal/temporary overrides, daylight-saving behavior, exact money, valid/invalid inquiries, safe escaping, phone-only contact, flexible dates, CSRF, honeypot/rate limiting, duplicate retries, storage failure, mail outage and authenticated staff updates. Fixtures use an in-memory database and a fake notifier; no real orders, bookings or staff emails were sent.

The user elected to perform browser/visual review. This build has not been declared visually verified on desktop/mobile. Start by checking `/food-and-ice-cream`, `/ice-cream`, `/mini-golf`, `/gatherings` (including validation errors and keyboard use), `/visit`, `/gallery` and the draft menu preview at narrow phone/tablet/desktop widths.

Open business items are consolidated in `OWNER_REVIEW.md` and the authenticated review screen. The inventory DOCX and seventh menu image were not provided; six images were recovered and archived. Full current menu/price completeness cannot be certified until source coverage and business approval are resolved. The public menu provides category browsing and current provider/contact links while the full transcribed menu is staged privately. No pie ordering workflow is enabled for the expired 2025 campaign. Provider transaction behavior, stock, fees, reservation availability and successful purchases were not tested.
