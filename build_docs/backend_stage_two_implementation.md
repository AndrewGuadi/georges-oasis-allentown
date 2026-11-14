# Backend stage two — implementation and operation

Implemented locally November 11, 2026, from [the build specification](backend_stage_two.md). Public hosting, DNS and live mail configuration were not changed.

## Staff entry points

Open `/admin` with `username` / `password` for the existing local development bootstrap. Once a named account exists, use its credentials: the shared bootstrap stops working. Production continues to reject the development credentials and requires the production secret/host configuration in README.

| Screen | What staff can do |
| --- | --- |
| `/admin/menu` | Search/filter categories and items, create/duplicate, reorder, edit descriptions/prices/options/photos, mark unavailable, save draft, compare, publish, pause, archive and restore revisions |
| `/admin/settings` | Owner-only public-price switch and specials weekdays |
| `/admin/specials` | Weekly menus and recurring offers, plus links to dated deals/coupons |
| `/admin/promotions/new` | Dated offer editor with separate draft/publish actions, image upload and saved-draft preview |
| `/admin/media` | Upload validated images and browse new/existing restaurant photos |
| `/admin/inquiries` | Type tabs, text/phone/internal-note search, combined filters, date sorting, pagination and owner CSV export |
| `/admin/inquiries/<id>` | Original submission, internal notes, status/history, assignment, follow-up date, archive/restore and notification retry |
| `/admin/staff` | Owner role/access changes with password confirmation |
| `/admin/password` | Named-account password change and session revocation |

Inquiry states are New, Contacted, Tentative reservation, Confirmed, Cancelled, Fake / spam and Other. Cancellation/Other/reopening require a reason. General/Other requests cannot become reservations without reclassification. Workflow changes do not send customer confirmations or reserve capacity. Receipt access remains restricted to the submitting session.

Owner and inquiry staff can access customer records; editors manage content/media. Named accounts have eight-hour absolute and 30-minute idle session limits. Password/access changes invalidate existing sessions. Provisioning and recovery are operator CLI actions, with no public registration/reset service.

## Data and publication

The local SQLite database was backed up consistently to `/tmp/oasis-before-stage-two.sqlite` before upgrade. That is a session recovery artifact, not a production backup policy. The local database now has both new migrations applied and 228 imported content records, including the original seven categories and all 212 menu items. All original item IDs, source metadata, variants/additions and feature/photo relationships are preserved. Public prices remain off.

Content uses `ContentRecord` relational identities/parents/order/version counters and immutable `ContentRevision` snapshots, with independent draft/published pointers. This intentionally consolidates the specification's separate category/item/special revision tables into one validated revision mechanism. Variant/addition/dish values remain revision-owned JSON; all monetary values in those snapshots are integer cents. Each submitted item review covers its complete set of prices/options. Separate relational tables store staff, inquiry notes/history, audit events, media metadata, throttling counters and the notification outbox.

Published descriptions can remain public while stale prices stay hidden. Enabling the global switch exposes only item prices reviewed in the submitted version. All regular-menu price surfaces, options and feature cards follow that rule. Weekly/recurring special prices require explicit review to publish. Global regular-menu pricing does not suppress separately approved special prices.

Legacy `closed` inquiries migrate to `other` with an explanatory history entry; nothing infers a confirmed or cancelled outcome. Original customer messages remain separate from append-only staff notes. Optimistic version checks reject stale staff edits with a recoverable conflict screen.

SQLite FTS5 with the trigram tokenizer indexes literal substrings of three or more characters, including internal notes and normalized phones. Database triggers keep it synchronized within the same transaction, including rollbacks and deletes. Short searches use bounded SQL pagination but can scan more data; the UI suggests at least three characters. The index contains private customer data and belongs in the same retention/deletion/backup controls as the inquiry tables.

Only menu/specials domains move from JSON. Business hours, story, golf facts and other editorial content remain in `content/site.json`. The adapter retains existing public-template contracts and explicit `SITE_CONTENT` test fixtures. Catalog import is atomic/idempotent and refuses changed-source overwrites of an existing import. Do not continue editing migrated domains in JSON after cutover.

## Setup on another installation

Back up the existing database, uploads/media and session secret first. Use an application-consistent snapshot and verify it can be restored.

```bash
.venv/bin/flask --app app db upgrade
.venv/bin/flask --app app import-catalog --dry-run
.venv/bin/flask --app app import-catalog
.venv/bin/flask --app app check-content
.venv/bin/flask --app app db check
.venv/bin/flask --app app staff-user restaurant-owner --role owner --name "Restaurant owner"
```

The last command prompts privately for a matching 15–256 character passphrase; it also resets an existing account and revokes prior sessions. Use `--role editor` or `--role inquiry` for additional staff. Keep usernames unique. Existing production `OWNER_USERNAME`/`OWNER_PASSWORD_HASH` settings remain required at startup for compatibility, but named accounts take over sign-in once provisioned.

Start the HTTP server through the existing Gunicorn configuration. Keep `instance/` on durable local disk, including `media/`, legacy `uploads/` and the session key. Set a stable `ABUSE_KEY` in host secrets for throttling identities; it otherwise uses the existing session signing key. Do not expose this SQLite/persistent-disk setup on ephemeral or multiple independent hosts. PostgreSQL driver/provisioning, its search indexes and object storage need a separately verified host-specific setup; this implementation was tested on SQLite, not PostgreSQL.

The data-bearing stage-two migration deliberately refuses an automatic downgrade that would discard staff revisions/history. Roll back to a compatible application using the expanded schema or restore a rehearsed backup with writes stopped and an explicit plan for newer inquiries. The FTS-only migration is reversible. Never reset the live database just to roll back application code.

## Notification worker and upkeep

Public submissions commit the inquiry, initial history and outbox event before returning a receipt. The web process never sends SMTP. Configure `INQUIRY_RECIPIENT`, `INQUIRY_SENDER`, approved SMTP settings, and `STAFF_BASE_URL=https://your-real-domain` before enabling delivery. Email contains a reference and private staff link rather than the customer message. When unconfigured, records save with a visible `not_configured` state.

Run a supervised worker alongside the web process:

```bash
.venv/bin/flask --app app process-notifications --watch
```

Alternatively schedule `process-notifications --limit 25` at least once per minute. Jobs have expiring claims, five bounded attempts and backoff; worker heartbeat is saved as `BackendSetting.worker_heartbeat`. Staff can retry failed jobs. SMTP delivery is at least once: a send followed by a database failure can duplicate a notice. A final expired lease is surfaced as failed rather than silently stuck. The inbox remains the source of truth.

Schedule this daily:

```bash
.venv/bin/flask --app app backend-cleanup
```

Cleanup removes old abuse counters and unreferenced orphan upload files older than one day. It preserves inquiry records and saved media metadata/revision references. The owner must choose retention periods and deletion procedures for inquiries, staff notes, the FTS index, exports and backups before production launch; no invented customer-data expiry is applied.

Back up SQLite consistently along with uploads/media and the session secret. Restore testing and backup automation must be configured on the actual host; the development backup alone does not meet production recovery requirements.

## Protection and performance

Submissions retain CSRF, session-bound expiring tokens, honeypot validation and durable idempotency. Shared atomic database counters enforce client/session limits across processes, with a separate form-fetch throttle. Public submissions have a 32 KiB cap enforced before CSRF parsing; image files have a 4 MiB/20-megapixel limit under the 5 MiB total request cap. JPEG/PNG/WebP are decoded, oriented, stripped and regenerated into immutable responsive WebP derivatives. Draft media is private; published media has cacheable URLs. No arbitrary customer attachments, executable formats or remote URL ingestion is accepted.

The app intentionally uses `remote_addr` and does not trust arbitrary forwarded headers. On the actual host, configure the trusted proxy chain and per-customer edge limits so all users do not appear as one shared proxy address. Challenge providers, broader flood controls and automatic similarity quarantine remain optional follow-up work; they are not advertised as active defenses here.

List queries are paginated and use stable sorting. SQLite substring search is indexed. Catalog snapshots validate database revision/version signatures before reuse, so other workers' publications invalidate them. Anonymous regular-menu/dessert pages have a cache lasting only until the next second boundary (or earlier editorial validity boundary); every hit rechecks the database generation. Host/scheme are part of the key. Sessions, forms, previews and receipts never use that cache. Cache hits do not mask database failures.

The isolated [performance report](backend_stage_two_performance.json) uses 50,000 synthetic inquiries, 150,000 notes, ten concurrent in-process sessions, and 30 requests per route on this workspace's SQLite installation. Final p95 values: unfiltered inbox 357 ms, filtered inbox 168 ms, matching-note search 312 ms, no-match search 338 ms, anonymous menu cache hits 34 ms. The menu's first cold request took 470 ms, including initial template compilation; cold latency still needs measurement/tuning on the production host. These are workspace measurements, not production guarantees. Earlier unindexed note search exceeded six seconds under this same workload and was replaced.

## Verification and remaining launch work

Final verification: 71 automated tests passed; the isolated Chromium workflow passed; `db check`, `check-content`, Python compilation and whitespace checks passed.

The full automated suite covers public pages plus import reconciliation, exact prices, publication isolation, legacy inquiry migration, every status, notes, search rollback consistency, assignment permissions, stale writes, image privacy, CSV safety, concurrent limits, private receipts, bounded submissions and worker lease recovery. The browser check uses a temporary database and real Chromium/CSRF to exercise submission → receipt → login → note/search → tentative status, mobile layouts and draft/public separation. No real inquiries, staff emails, orders or reservations were sent by these checks.

Reproduce the checks:

```bash
.venv/bin/python -m unittest discover -s tests
PLAYWRIGHT_BROWSERS_PATH=/tmp/oasis-browsers .venv/bin/python scripts/stage_two_browser_check.py
.venv/bin/python scripts/backend_benchmark.py
```

The browser path above is specific to this workspace; set it to the actual Chromium installation elsewhere. Browser screenshots/logs and benchmark scratch databases use `/tmp`; preserve desired artifacts before the session expires. The homepage's existing test was updated to validate its image assets rather than require the outdated exact count of nine.

Before a production release: provision named staff, approve current prices/specials, configure persistent storage and SMTP/worker supervision, assign inbox monitoring, agree retention/recovery targets and rehearse backups on the chosen host. MFA, a service-hours editor, real capacity/deposit/reservation management, POS/payment integration, customer acknowledgements and object-storage deployment remain outside this implemented stage.
