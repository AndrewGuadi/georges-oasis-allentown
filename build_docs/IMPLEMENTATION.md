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

The production pass adds automated Chromium checks of all ten public pages at 320, 390, 768 and 1440 pixel widths, including image loads, overflow, navigation and form validation. Screenshots are generated in `/tmp/oasis-browser`; rerun `scripts/browser_check.py` for future changes. Start by checking `/food-and-ice-cream`, `/ice-cream`, `/mini-golf`, `/gatherings` (including validation errors and keyboard use), `/visit`, `/gallery` and the draft menu preview at narrow phone/tablet/desktop widths.

Open business items are consolidated in `OWNER_REVIEW.md` and the authenticated review screen. The inventory DOCX and seventh menu image were not provided; six images were recovered and archived. Full current menu/price completeness cannot be certified until source coverage and business approval are resolved. The public menu provides category browsing and current provider/contact links while the full transcribed menu is staged privately. No pie ordering workflow is enabled for the expired 2025 campaign. Provider transaction behavior, stock, fees, reservation availability and successful purchases were not tested.


## Production readiness pass (October 2026)

Optimized WebP derivatives retain the eight original photographs and reduce total image bytes from approximately 6.44 MB to 0.96 MB. Regenerate with `scripts/optimize_images.py`. Menu and ordering journeys now prioritize the live provider, hourly links stay within the site, and homepage deals are visible inline without JavaScript. Sharing previews, a favicon, restaurant structured data and descriptive homepage metadata are included.

Shared security headers, custom failure pages, CSRF recovery preserving event details, database-backed owner login throttling, eight-hour owner sessions, trusted-host enforcement and production refusal of demo credentials are implemented. Migration `3a72d189c401` adds the login-attempt table. Use the Gunicorn configuration and deployment instructions in README; production requires Flask 3.1 or later for trusted hosts.

Live deployment still requires a known hosting destination, actual owner credentials, approved current business data, and staff inquiry monitoring. The published legacy hours page was checked on October 13, 2026 and still labels its restaurant hours “SUMMER 2026”; it is not evidence for approving current autumn hours. No draft menu prices, golf rates or event policies were automatically approved. No live transactions or staff emails were sent.

Verification for this pass: 28 automated tests passed; all 40 public page/viewport combinations passed; mobile menu keyboard dismissal, phone/email selection and form-error focus passed. Automated axe checks against WCAG A/AA rules returned no violations on the ten public pages at a 390 px viewport after fixing a mini-golf caption contrast issue. These checks supplement visual review and do not certify accessibility compliance. The CSS build, Gunicorn configuration validation and Python dependency consistency check passed.

`npm audit --omit=dev` reports zero runtime vulnerabilities. The full audit still reports seven advisories in the existing Tailwind 3 build-tool dependency tree, including unpatched pattern-parsing dependencies. Node is used only to compile trusted repository templates; it is not required or included in the Flask runtime. A Tailwind major-version migration remains a separate tooling task; do not process untrusted templates with this build chain.

## Mini golf page and internal navigation update

The mini golf page now presents the user-approved $8 adult / $6 child rates, eligibility (58 inches and under or under 12), April–November season, 45-minute last-start rule, and group package options. Entire-course reservations are inquiry-based for groups of 20 or more. Daily course hours remain unapproved; restaurant and dinner hours do not stand in for golf hours. Golf CTAs stay on this website or call the business. Legacy menu/golf/hours destinations in `external_links.py` now use internal routes; historical source URLs remain in editorial metadata for provenance.

The course gallery reads every `media` entry with `group: "Mini Golf"` from `georges_oasis/content/site.json`. It currently uses the two existing course photographs. To add supplied course images, place originals in `static/images`, add descriptive `file`, `subject`, `caption`, `group` and source/rights metadata to that media list, and run `scripts/optimize_images.py`. The golf gallery and general Gallery page will both include them. Keep subjects/captions specific to the real photograph; do not invent hole numbers. The on-page viewer supports previous/next, arrow keys, Escape and return focus; mobile visitors can swipe the thumbnail strip. Without JavaScript, photo links still open the local image.
