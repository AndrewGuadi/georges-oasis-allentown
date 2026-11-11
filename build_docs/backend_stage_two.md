# Backend stage two — George’s Oasis

Prepared November 11, 2026. This is a build specification based on the current repository, not a record of implemented stage-two features. Priority order: accurate data and durable submissions, fast customer/staff workflows, then convenience features.

Implementation and operating notes: [backend_stage_two_implementation.md](backend_stage_two_implementation.md). The specification below records the original target; the implementation notes identify the actual schema, verification and remaining host-specific launch work.

## 1. What we already have

Extend the existing Flask application, SQLAlchemy models, Flask-Migrate/Alembic migrations, Jinja templates, Flask-WTF CSRF protection, Pillow image processing, and Gunicorn deployment. Preserve public URLs and the current visual design.

| Area | Current implementation | Stage-two work |
| --- | --- | --- |
| Staff access | `/admin/login`, development credentials `username` / `password`, environment-configured production credentials, hashed passwords, eight-hour sessions, database-backed login throttling | Named staff accounts, permissions, password management, session revocation and audit attribution |
| Menu | `content/site.json`, `content.py`, public menu and private preview | Database-backed category/item/variant/add-on editing, image selection/upload, publication controls |
| Prices | 212 items across seven categories; exact decimal formatting; `menu_pricing.show_prices=false` | Preserve hidden prices; review and publish current prices explicitly |
| Specials | Database `Promotion` editor for dated deals/coupons, image uploads, scheduling and homepage toggles; recurring offers and daily special menus live separately in JSON | One staff Specials section managing all three existing content types |
| Inquiries | `/gatherings` saves `Inquiry` before receipt; session-bound submission tokens; honeypot; rate limits; optional SMTP notifications | Typed, searchable, filtered inbox, expanded statuses, internal notes, assignment and follow-up |
| Inbox | `/admin/inquiries` loads every record; detail supports `new`, `contacted`, `closed`; notification retry | Database pagination, indexed filters, history, optimistic concurrency, asynchronous notification retries |
| Protection | CSRF, security headers/CSP, trusted hosts, secure production cookies, private receipts, 5 MiB request limit, image decode/re-encoding | Stronger shared abuse controls, field-specific limits, media lifecycle and operational visibility |

Evidence: `georges_oasis/{__init__,admin,models,content,inquiries,security,oasis_images}.py`, `georges_oasis/public/routes.py`, current `content/site.json`, admin/public templates, migrations, and `tests/`.

Older `README.md`, `build_docs/IMPLEMENTATION.md` and `OWNER_REVIEW.md` contain historical draft-menu descriptions. Current code/data take precedence for this plan: the menu contains 212 items, prices are intentionally suppressed after October 26 owner feedback, and Wednesday/Thursday/Friday special menus exist as empty drafts. Preserve source/review metadata and unresolved business facts. Importing data must not imply fresh approval.

## 2. Team assignment and delivery ownership

Use three core engineers, part-time operations support, and one restaurant decision-maker. These are proposed assignments; this document does not launch agents or implementation work.

| Role | Assignment and deliverables | Accountability |
| --- | --- | --- |
| Backend lead / data engineer | Schema, migration/import tooling, publication service, authentication/authorization, transaction boundaries, inquiry query service and outbox worker | Owns shared contracts, data integrity, code integration and migration rollback |
| Staff-interface engineer | Responsive dashboard, menu/media editors, Specials workspace, inbox/search/detail/notes, preview and validation feedback | Owns fast, accessible daily staff workflows and public-template integration |
| QA / security engineer | Independent source/import reconciliation, permission/abuse/concurrency testing, migration rehearsal, browser journeys and performance measurements | Owns release evidence and regression gates; starts with fixtures/contracts in phase 1 |
| Operations engineer, part-time | Persistent storage, secrets, trusted proxy/rate limiting, worker/scheduler supervision, backups/restores, metrics and deployment | Owns operational readiness and recovery rehearsal |
| Owner or designated staff representative | Price/specials approval, inquiry taxonomy, staff permissions, monitoring rota, response expectations and retention decisions | Owns business accuracy and acceptance of actual staff workflows |

The backend lead defines schemas, enums, route/form contracts, publication rules and representative fixtures before parallel implementation. Interface work can then proceed against fixtures while persistence is built. QA reviews each slice as it lands. One owner per shared module; coordinate edits to `models.py`, `admin.py` and `content.py` through the lead.

Suggested sequence, subject to source quality and owner review:

1. **Foundation, 2–3 working days:** baseline checks, schema/contracts, named accounts, migration scaffolding, fixtures, threat/performance baseline.
2. **Two parallel slices, 4–6 days:** menu/media/specials editing and typed inquiry workflow. Lead supplies services; interface engineer integrates forms; QA tests incrementally.
3. **Integration, 2–3 days:** public content adapter, outbox worker, shared throttles, audit/concurrency behavior and operating instructions.
4. **Acceptance, 2–3 days:** migration and restore rehearsal, realistic load tests, owner price review, staff mobile walkthrough and release checks.

This is a planning estimate of roughly two to three weeks, not a delivery commitment. Gate each phase on its acceptance evidence. Missing approved prices delay price publication, not a usable backend with prices hidden.

## 3. Staff experience and scope

### Dashboard and access

Provide navigation for Dashboard, Menu, Specials, Inquiries, Media and Settings. Show new/overdue inquiries, follow-ups due, failed notifications, upcoming/expiring specials and unreviewed prices. Counts link to the corresponding filtered lists. Loading the dashboard never marks inquiries contacted.

Retain username/password sign-in. Keep `username` / `password` as explicit local-development defaults only, preserving the existing production rejection of those credentials. Production provisioning creates a named owner using a secure CLI prompt; no default public account and no password in source/history/logs. Migrate away from the single environment account before switching the login implementation; preserve recovery access during cutover.

Roles: **Owner** manages accounts/settings, publishes and restores content, exports and authorizes deletion; **Editor** edits/publishes menu and specials and manages media; **Inquiry staff** works inbox/notes/status/follow-ups. Enforce permissions in server handlers/services, including direct URLs and object access. Disable rather than delete staff referenced by history. No public staff registration.

Store only password hashes. Allow password-manager paste/autofill, long passphrases and generic login errors. Provide authenticated password change and an audited operator CLI reset; email reset is deferred until a verified delivery/recovery process exists. Password changes/disabling accounts increment a session version checked on every authenticated request. Require fresh authentication for account changes, exports and deletion. Retain eight-hour absolute expiry and add a configurable idle expiry. Production login uses HTTPS, CSRF, secure cookies and throttling by both account and trusted client identity. See [OWASP authentication guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).

### Menu, prices and media

- Edit/reorder categories and item groups; create, duplicate, edit, hide, temporarily mark unavailable and archive items. Preserve stable imported string IDs used by feature cards and anchors.
- Edit name, description, inclusions, price note, exact base price, priced variants, add-ons and availability. Archive rather than erase referenced items. Provide menu search and category/publication/availability filters.
- Choose existing photographs from the packaged image manifest or upload a new image; edit alt text/caption and preview the actual public card. Preserve category photos, group photos and existing featured-item relationships.
- Separate **Save draft**, **Preview**, **Publish**, **Pause** and **Archive**. Editing published content creates a draft revision while the last published revision remains public. Show a before/after comparison and explicit price changes before publication.
- Store prices as integer USD cents, parsed through `Decimal` from validated form strings. Reject negatives, nonfinite values and excess decimals; never silently round or use binary float. Preserve the distinction between missing price and zero. Explicit free items require owner confirmation.
- Keep global public-price visibility off after import. Each base/variant/add-on price has a current-review marker; changing it invalidates that marker until reviewed. When global visibility is enabled, show only reviewed prices belonging to published content. Never leak stale prices through notes, feature cards, downloadable source menus or structured data.
- Imported item approval remains separate from price approval: existing descriptions can remain published while prices stay hidden. Source scans remain historical reference material. Do not advertise them as a current priced menu.
- Preview uses the same rendering/formatting as the public site. Provide unsaved-change warnings, field errors and success messages only after committed saves.

Media uploads are staff-only. Keep the existing 5 MiB total request cap; enforce a 4 MiB file cap and 20-megapixel decoded limit. Verify JPEG/PNG/WebP by decoding, reject animated/multiframe files, apply orientation, strip metadata, and generate WebP derivatives at roughly 400/800/1600 pixels without upscaling. Do not accept SVG, arbitrary URLs or customer attachments in this phase. Generate random immutable storage keys; never use supplied filenames as paths. These controls follow the layered approach in [OWASP file-upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).

Use persistent disk on a single persistent host; use object storage before any ephemeral or multi-host deployment. A storage adapter supports both without changing content records. Stage files, finish validation/derivatives, then attach ready media in a database transaction. Clean abandoned files after a grace period; do not delete media referenced by published or restorable revisions. Public media receives content-hashed URLs and long cache lifetimes; draft-only media requires staff access. Add a public media route rather than inheriting `/admin/images/` no-store caching for new assets. Preserve existing promotion-image URLs during migration.

### Specials

One workspace exposes **Weekly menus**, **Recurring offers**, and **Dated deals/coupons**, preserving their different meanings. Reuse and extend `Promotion` for dated offers rather than creating duplicate campaigns.

- Weekly menus: confirmed weekday, title, photo, ordered dishes/descriptions/optional reviewed prices, availability note and publication state. Wednesday/Thursday/Friday remain configured; no empty draft becomes an advertised menu.
- Recurring offers: weekday, local start/end, date range, terms, inclusions and optional reviewed price. Require complete eligibility and timing before publishing. Stage two supports same-day recurring windows; overnight recurrence remains unsupported with a clear validation error.
- Dated offers: title/body, image, coupon code, eligibility, UTC start/end, enabled/approval flags and placements. Keep existing deal/coupon homepage toggles.
- Duplicate a past special into a draft, pause immediately, preview, and inspect scheduled/live/expired states. Publish intentionally; merely uploading or saving must not approve an offer.
- Store instants in UTC and enter/display business time in `America/New_York`. Windows include the start and exclude the end. Preserve rejection of ambiguous/nonexistent dated input; require staff to select an unambiguous time.
- Generate homepage, `/specials` and related feature copy from the same selectors. Replace hardcoded specials-day text in `templates/public/specials.html` with configured days so changes remain consistent.
- A future date/weekday alone never proves a special is available: approval, enabled state, validity, schedule and required terms must all agree. Preserve useful call-the-restaurant fallbacks.

### Inquiry inbox

Separate **request type**, **occasion**, **interests**, **workflow status**, **notification status**, and **archive state**. Existing event inquiries remain event inquiries even when they include golf, dining and dessert interests.

Initial types: `event`, `mini_golf_group`, `general`, `other`. Backfill every current `/gatherings` record as `event`; do not infer a primary type from multiple interests. Offer a primary request-type choice on the existing form. Keep event fields conditional for event/golf requests; general/other require name, contact and message. Record the source route server-side. New standalone forms are optional future additions, not necessary for typed storage.

| Stored status | Staff label | Behavior |
| --- | --- | --- |
| `new` | New | Default on accepted submission |
| `contacted` | Contacted | Staff records that contact was attempted |
| `tentative_reservation` | Tentative reservation | Provisional arrangement; no automatic customer confirmation |
| `confirmed` | Confirmed | Staff explicitly records an agreement made with the customer |
| `cancelled` | Cancelled | Require internal cancellation reason |
| `spam` | Fake / spam | Quarantine from normal work queue; reversible |
| `other` | Other | Require explanatory internal note |

Use the corrected spelling “tentative”; include “cancelled” once. Widen `staff_state` beyond its current 20 characters because `tentative_reservation` needs 21. Require an explanatory note to reopen terminal states or revert confirmed to tentative. All transitions are explicit, validated and recorded; opening a record never changes status. Non-booking request types cannot enter tentative/confirmed until reclassified. Confirmation here is a staff workflow record, not capacity management, a deposit, a provider reservation or an automatic email.

Inbox requirements:

- Tabs/counts by type; combine type, status, occasion, interest, received-date range, preferred-event-date range, assignee, follow-up due and notification-state filters. Exclude spam/archived by default with visible inclusion controls.
- Search reference, customer name, normalized contact, customer message and internal notes. Case-insensitive text matching; normalized phone-digit matching; support punctuation in exact references/email. Cap queries at 120 characters and escape SQL wildcard literals. Bind all values and allowlist sorting.
- Paginate in SQL: 25 rows by default, maximum 100, stable newest-first order on `(received_at, id)`. Preserve filters/search while navigating and returning from detail; accessible empty/error states and clear-filter controls.
- Detail shows original submission, call/email actions, assignee, follow-up date, staff-only notes and chronological status/history. Keep customer `notes` immutable as submitted; staff notes are separate, author-attributed entries with bounded length and append-only corrections.
- Set due dates and surface overdue work in the dashboard; assign to active inquiry staff/owner. Provide a simple preferred-date list, without implying availability or preventing double booking.
- Archive/restore rather than default hard delete. Owner-only filtered CSV export escapes formula-leading values, is audited, and never uses a public share URL. Apply an owner-approved retention policy to records, notes, exports, backups and abuse data.
- Prevent silent overwrites: carry `version_id` with edits; on stale update return a conflict view with current values and the unsaved change. Do not automatically retry a conflicting staff decision.

## 4. Database design

Default local/development database remains SQLite. Prefer managed PostgreSQL for production concurrent staff work, a worker and multi-instance operation; add a compatible driver and test that target before cutover. SQLite can serve a small single-host deployment with persistent local disk and short writes, but has limited concurrent writing; see [SQLite deployment guidance](https://www.sqlite.org/whentouse.html). Do not put its database file on a shared network volume. Database-engine migration is a separately rehearsed deployment step, not a prerequisite to writing the editors.

All new tables use explicit foreign keys, non-null/default rules, timestamps and validation constraints. Enable SQLite foreign-key enforcement. Use integer primary keys except where existing stable content string IDs must survive. Match the current UTC-naive instant convention consistently during this phase; convert at boundaries and document any later timezone-column migration. Business dates remain SQL `DATE` and recurring local times remain wall-clock values plus the business timezone.

| Table/model | Fields and relationships |
| --- | --- |
| `StaffUser` | Unique normalized username, display name, password hash, role, active, session version, created/updated/last-login timestamps |
| `MenuCategory` | Stable unique string ID, order, published/draft revision pointers |
| `MenuCategoryRevision` | Category FK, revision number, name/intro, group order, category/group media references, source metadata and author/review timestamps |
| `MenuItem` | Stable unique string ID, category FK, order, published/draft revision pointers, availability, archive timestamp, version counter |
| `MenuItemRevision` | Item FK, revision number, name/group/description/inclusions/price note, nullable base cents, price-review fields, media FK, publication metadata and author |
| `MenuVariant`, `MenuAddon` | Item-revision FK, stable option key, label, integer cents, order, review fields; unique key per revision |
| `ContentSettings` | Singleton, global price visibility/review metadata, configured specials weekdays, publication generation/version counter |
| `MediaAsset` | Storage kind/key or packaged manifest key, checksum, MIME/dimensions/bytes, derivative keys, alt/caption/source, readiness/visibility, creator/timestamps |
| `WeeklySpecialMenu`, `WeeklySpecialRevision`, `WeeklySpecialItem` | Stable menu ID, weekday, publication pointers; revision title/media/note/metadata; ordered revision-owned dishes with optional reviewed cents |
| `RecurringOffer` plus revision records | Stable imported ID, publication pointers; weekday/local time/date bounds, terms, reviewed price and source/review metadata |
| Existing `Promotion` | Preserve IDs and fields; add media FK, eligibility/placement fields, timestamps/version; use a draft revision payload/table so edits do not mutate live content before publishing |
| Existing `Inquiry` | Preserve ID/reference/submission key/contact and original fields; add type, source route, assigned-user FK, follow-up timestamp, updated/archive timestamps, normalized search fields and version; widen staff status to `String(32)` |
| `InquiryNote` | Inquiry FK, author FK, plain text body (maximum 4,000 characters), created timestamp; corrections append a new entry |
| `InquiryStatusHistory` | Inquiry FK, previous/new state, actor FK, reason, timestamp; required for every transition in the same transaction |
| `AuditEvent` | Actor, action, entity type/ID, timestamp, sanitized changed-field summary; retain content history by revision, avoid duplicating inquiry PII in audit blobs |
| `NotificationOutbox` | Inquiry FK, unique event/delivery key, state, attempts, next-attempt time, lease owner/expiry, sanitized last error, sent timestamp |
| Existing attempt tables | Keep login/inquiry attempt records for compatibility; add composite `(client_key, attempted_at)` indexes; move expiry cleanup out of interactive requests |

Published revision pointers make publication atomic and drafts invisible. Published revision contents are immutable; restoring an older version creates a new revision and audit event. Category/item/media pointer updates and publication generation increment commit together. Define explicit ORM foreign-key paths for revision pointers and parent FKs to avoid ambiguous relationships. Use restrictive deletion for history and referenced media.

Constraints: unique content/revision keys, unique submission/reference/delivery keys, allowlisted status/type/role values, cents >= 0, weekday 0–6, end after start and valid referenced parents. Pair constraints with friendly form validation. Lock or version the content-settings row when allocating publication generations so concurrent publishers cannot reuse a generation.

Indexes: inquiry `(staff_state, received_at, id)`, `(inquiry_type, received_at, id)`, `(assigned_user_id, follow_up_at)`, `preferred_date`, `(notification_state, received_at)` and `(archived_at, received_at, id)`; notes/history `(inquiry_id, created_at, id)`; outbox `(state, next_attempt_at)`; menu category/order and offer validity fields. Add further indexes only with query-plan evidence.

Search uses a bounded SQL `EXISTS` query for notes to avoid duplicate inbox rows. Ordinary B-tree indexes will not accelerate arbitrary `%substring%` text search. Benchmark at 50,000 inquiries/150,000 notes; if the target is missed, use PostgreSQL trigram indexes for substring fields, or SQLite FTS5 with documented token-search behavior. Keep reference/contact lookups indexed and test parity where engines differ. Maintain any search document transactionally and include deletion/retention handling; do not use an eventually consistent external search service in this phase.

## 5. Migration and integration

1. Inventory database schema/row counts, JSON IDs, all 212 items/options, photo/group/feature references, existing promotions/uploads and legacy inquiry-state counts. Back up database, JSON, uploads and session key; rehearse restoration with writes paused or a database-consistent snapshot.
2. Add Alembic revisions after current head `3a72d189c401`; do not edit applied migrations. Create new tables and nullable fields first, backfill, validate, then enforce constraints. Use SQLite batch alteration where required.
3. Build a repeatable, versioned import CLI with dry-run report, source checksum and transaction rollback. Preserve category/item/offer IDs, exact cents, options, order, metadata, images and featured links. Upsert only import-owned untouched records; refuse to overwrite subsequent staff edits. Rerunning the same import produces no duplicates or approvals.
4. Import JSON menus, recurring offers and weekly menus into their respective models. Preserve the global hidden-price setting and empty weekly drafts. Keep unrelated business hours/story/golf/editorial data in JSON for this stage. Check all category and item counts and every source amount, not only total rows.
5. Backfill inquiries as `event`, new normalized fields, timestamps/version. Preserve `new`/`contacted`; map legacy `closed` to `other` with a migration-history explanation, because closed does not prove confirmed or cancelled. Report unknown states for manual mapping rather than guessing. Preserve original customer notes and notification state.
6. Seed a named production owner through a secure CLI using existing approved credentials or a newly prompted password. Verify successful access before retiring environment-only authentication. Never seed the demo credentials in production.
7. Introduce `services/menu.py`, `specials.py`, `inquiry_workflow.py`, `media.py`, `auth.py` and `notifications.py` (names may follow repository conventions). Keep HTTP handlers thin. Centralize publication/status validation so admin, preview, public pages and worker agree.
8. Adapt `content.py:public_content()` to supply the existing template shapes from database publication selectors for migrated domains. Preserve `SITE_CONTENT` as an explicit test/preview fixture path. Keep stable feature IDs working, extend `photo_url`/image macros for uploaded assets, and validate migrated plus remaining JSON content via `check-content`.
9. Feature-flag database content until parity checks pass; then switch all public menu/special readers together. Do not silently fall back to old JSON on database failure: that can resurrect stale prices or paused offers. Show a safe contact fallback and operational error instead.
10. Move SMTP behind the transactional outbox. Keep existing POST/redirect/receipt URLs and session receipt authorization. Update staff tests/templates for all statuses; retain existing offer editor URLs via redirects/adapters where practical.
11. Freeze legacy writes during final migration, reconcile counts/references, deploy the compatible app and worker, verify, and reopen writes. Retain source snapshots read-only. Once staff edits begin, rollback must use a compatible app against the expanded schema; do not restore old JSON/database and lose new inquiries. Rehearse forward repair and database-engine copy separately.

Suggested staff routes: `/admin/menu`, `/admin/menu/items/<id>`, `/admin/specials`, `/admin/media`, `/admin/inquiries`, `/admin/inquiries/<id>` plus explicit POST actions for notes/status/assignment/publication. Use ordinary server-rendered forms and POST/redirect/GET; a separate SPA or public write API is unnecessary.

## 6. Durable submissions, spam protection and notifications

Accepted submission path:

1. Enforce proxy/body limits and trusted-client abuse limits before expensive work; validate CSRF and the existing expiring session-bound submission token.
2. Look up the unique submission key; an authorized retry returns the existing receipt without creating another record or delivery event. Invalid/reused keys from another session reveal nothing.
3. Validate type-specific fields, lengths, contact format, dates, enum values, honeypot and risk signals. Never trust a posted status, source route or assignee.
4. In one transaction, insert the inquiry, initial history event and outbox event (when delivery is configured). Commit before claiming success. Handle unique-key races by retrieving the existing authorized inquiry.
5. Return the private receipt promptly. A supervised worker sends staff notices separately. Failure to commit returns a recoverable error preserving form values; no success receipt for unsaved requests.

Layer abuse protection rather than depending on a CAPTCHA:

- Retain CSRF, token expiry, honeypot and strict server validation. CSRF alone does not stop bots that fetch the form. Honeypot autofill behavior must be tested with real browsers/password managers.
- Starting policy: 10 accepted/invalid attempts per trusted client per 15 minutes and 5 per session; configurable and measured for shared Wi-Fi. Add account/client limits to login. Rate-limit token/form issuance at the edge to prevent cheap session rotation.
- Enforce atomic shared counters at the trusted proxy or a shared store across workers; the current count-then-insert database approach is insufficient for strict concurrent limits. Define an explicit trusted-proxy chain; never accept arbitrary forwarded headers. If no trusted client address is available, rely on session plus edge limits rather than blocking every visitor behind one proxy address.
- Add aggregate circuit breaking/alerts for floods; retain a phone fallback. Use `429` plus `Retry-After` for throttling and do not turn infrastructure failure into a false successful submission.
- Use hidden-field matches as strong evidence; excessive links/repeated text and implausibly fast completion are risk signals. Do not reject solely on speed, IP or email domain. Optional challenge only for elevated risk, with server verification, timeout and accessible retry/phone path; integrate any CSP/provider requirements only when chosen.
- Token retries are hard-deduplicated. A short-lived HMAC fingerprint of normalized contact/message can flag similar submissions for staff, but must not silently discard a legitimate second request.
- Clearly rejected bot traffic gets no inquiry receipt. Ambiguous submissions saved for review enter `spam` with an internal reason and no staff-email flood; the receipt still states only that the request was received. Provide restoration to `new` and false-positive review.
- Escape untrusted text everywhere; no submitted HTML or clickable arbitrary message links. Bound inquiry POST bodies to 32 KiB, retain name/contact/message limits, and accept only documented fields. Prevent header injection and never place customer data in log lines or query strings.
- HMAC client identifiers with a stable, dedicated abuse key; avoid retaining raw IPs in application tables. Keep abuse logs short-lived (initial proposal: 24 hours for attempt rows); have operations account for proxy-log retention too. Prune on a scheduled task with bounded batches.

Outbox delivery is at-least-once: claim due jobs atomically with expiring leases, commit the claim before network I/O, apply a short provider timeout, and retry with exponential backoff/jitter, for example 1, 5, 15, 60 minutes and 4 hours. After five failures, show a terminal alert with audited staff retry. Use a stable delivery key/provider idempotency where available. SMTP can duplicate a notice if sending succeeds but state recording fails; do not promise exactly-once email. A crash never deletes the inquiry. Default notifications contain a reference and staff link with minimal personal data. No automatic customer mail or booking confirmation in this stage.

## 7. Speed, correctness and operating targets

These are proposed acceptance budgets, not measurements of the current app. Measure p95 application/server times separately from network/browser timings, report hardware/data volume, and include cold/warm results.

| Operation | Acceptance target under representative load |
| --- | --- |
| Public content response | p95 server response <= 300 ms, no mail/storage-provider dependency |
| Inquiry commit and receipt redirect | p95 <= 750 ms excluding an optional challenge; no synchronous SMTP |
| Inbox list/filter/search | p95 <= 500 ms at 50,000 inquiries and 150,000 notes with 10 concurrent staff sessions |
| Normal staff save | p95 <= 500 ms excluding image processing; stale writes produce visible conflicts |
| Notification | First delivery attempted within 60 seconds of commit when configured and healthy |
| Publication | Visible on the next uncached read; any shared cache invalidates immediately, bounded stale lifetime <= 30 seconds |
| Recovery | Proposed RPO <= 24 hours and RTO <= 4 hours; owner accepts or upgrades backup frequency before launch |

Bound every list/query, eager-load only necessary relationships, eliminate N+1 queries, and query live promotions in SQL instead of loading all historical promotions into Python. Keep transactions short; no SMTP/image decoding inside a database write lock. Serve resized images with dimensions and responsive sources. Match derivatives to real display sizes.

Start public reads without a full-page cache; optimize measured bottlenecks first. If caching is needed, cache anonymous published content keyed by a database publication generation and expire no later than the next schedule boundary or 30 seconds. Per-process invalidation alone is insufficient across Gunicorn workers. Never cache staff pages, draft previews, inquiry forms with CSRF/session tokens or private receipts in a shared cache. Do not mix one visitor's form/session data with reusable public content.

Use integer version counters and explicit expected-version checks for all mutable staff records; test bulk updates separately because ORM version checking does not apply automatically to all bulk operations. See [SQLAlchemy version-counter documentation](https://docs.sqlalchemy.org/en/20/orm/versioning.html). Commit edits, history and audit together. Database failure must not produce a successful save banner.

Monitor response percentiles, database lock/conflict errors, failed saves, rejected submissions, false-positive spam restores, outbox depth/oldest age, worker heartbeat and backup age. Logs contain request IDs and inquiry references rather than messages/contact details. Staff see actionable mail-delay warnings and saved-record state. Persist uploaded media and session keys; test encrypted, access-restricted backups and restoration. Run worker/cleanup with process supervision, not ad hoc threads inside HTTP workers.

## 8. Verification and release gates

The QA engineer expands existing `tests/test_inquiries.py`, `test_promotions.py`, `test_content_rules.py`, `test_full_menu.py`, `test_owner_feedback.py` and `test_production.py`, adding focused suites as needed.

- **Migration:** empty database and populated upgrade; preserve every existing inquiry/reference/promotion, all 212 menu IDs, option cents, ordering, source fields and photo/feature links. Re-run import without changes; fail safely on conflicting edited data. Rehearse backup restore and compatible rollback.
- **Authentication:** production rejects demo defaults; every protected GET/POST respects roles; logout/expiry/disable/password change revoke access as specified; CSRF and direct-object access tests; no sensitive cache responses.
- **Menu:** hidden prices remain hidden across menu, dessert/home feature cards, metadata and source downloads. Review/publish exact cents and options; draft edits cannot change live content; unavailable/archive/restore behave consistently.
- **Specials:** homepage and specials agree; test start/end/weekday boundaries, pause, expiry, incomplete drafts and daylight-saving input rejection. Configured days replace hardcoded public claims.
- **Inquiries:** all seven statuses, typed form rules, combined filters/search, phone normalization, notes isolation, sorting/pagination, assignment, due dates and legacy `closed` mapping. Parallel staff saves cannot lose changes. Confirmed workflow state never sends a booking confirmation.
- **Reliability/abuse:** concurrent duplicate POSTs produce one inquiry/history/outbox event; database failure yields no false receipt; SMTP outage/worker crash/lease expiry preserve data; notification retry is bounded. Test forged proxy headers, shared networks, burst concurrency, honeypot, expired tokens, malicious input and quarantine restoration.
- **Media:** corrupt/oversized/decompression-bomb/multiframe uploads, path traversal, metadata stripping, draft access, durable derivative URLs, failure cleanup and referenced-image retention.
- **Browser/performance:** keyboard and screen-reader labels, errors preserving input, mobile staff work at 390 px and desktop, public layouts at 320/390/768/1440, end-to-end customer submission through staff note/status update. Measure the agreed workload against section 7 budgets using the actual production database engine.

Run `.venv/bin/python -m unittest discover -s tests`, migration checks, `flask --app app check-content`, and the existing browser checker when implementing. Rebuild CSS only if classes/styles change. Use fake notification transports and synthetic contact data; no live customer/staff messages or provider transactions during tests.

Launch requires passing integrity/security/reliability checks, reported performance results, verified staff access, persistent storage, a supervised worker, restore evidence, a named inbox monitor and an agreed retention policy. Owner can accept the backend while unverified menu prices/specials remain hidden. Document remaining business-source gaps explicitly.

## 9. Helpful additions and deliberate boundaries

Included because they reduce daily mistakes: draft/publish separation, previews, revision restore, price-review queue, internal notes/history, staff assignment, follow-up reminders, notification health, archived-record recovery, safe filtered export and duplicate-spam review.

Later candidates: holiday/service-hours editor using the existing schedule rules, approved ice-cream availability editor, saved inbox views, granular roles/MFA, verified customer acknowledgements and a reservation calendar after capacities/deposits/cancellation policies are settled. Payments, POS synchronization, online stock guarantees, automated booking acceptance, public account signup and customer attachments require separate specifications.

Owner decisions needed before release: current prices and the scope of publishing them; special dishes/terms/times; named staff and role assignments; notification destination and monitoring schedule; follow-up expectations; retention/export/deletion rules; hosting/storage/database choice; and accepted recovery targets. Development uses the conservative defaults above until these are settled.
