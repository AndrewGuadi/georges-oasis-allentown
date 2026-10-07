# George's Oasis Allentown

A Flask demo site for George's Oasis in Allentown, PA.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app db upgrade
flask --app app run --debug
```

The homepage is served at `/`. Public navigation follows `build_docs/proposed_sitemap.txt`:

- `/food-and-ice-cream`
- `/mini-golf`
- `/gatherings`
- `/specials`
- `/our-story`
- `/visit`

Each indented sitemap topic is a section with a stable anchor on its parent page. The old `/menu`, `/ice-cream`, `/parties`, `/about`, and `/order` routes were removed. View Menu opens the internal Food & Ice Cream page. Order Online opens FoodBooking; Order Delivery opens Grubhub. Table reservations open Google, group reservations use email, and hiring opens Facebook. These are outbound links only; no forms or service integrations are implemented.

External action destinations have one source of truth in `georges_oasis/external_links.py`. The app factory copies them into `app.config["EXTERNAL_LINKS"]` and an application-wide context processor exposes `external_links` to Jinja. Change a provider URL there and restart the application to update every applicable link. The shared `external_action` macro applies new-tab protections to HTTPS links and stable `data-action` identifiers for future analytics; email links remain in the same context. No tracking is installed.

`georges_oasis/public/sitemap.py` defines the navigation and section structure. Only these explicitly registered routes render page templates. Templates use Flask's default HTML autoescaping and `url_for` links; rendered HTML is not rewritten.

`templates/base.html` owns the public document shell and extension blocks (`title`, `description`, `extra_head`, `content`, `scripts`). Shared navigation, actions, and footer live in `templates/public/includes/`. The homepage extends the base directly; each other public page extends `public/section_page.html`, supplies its section copy, and can extend `page_extra`. Public styles live in `static/css/site.css`. Admin templates remain separate under `templates/admin/` with existing CSRF protection.

The existing Tailwind CDN and Google Fonts remain part of the prototype styling. The shared header includes an inline palm SVG, Facebook, ordering actions, and an accessible hours dropdown. Mobile visitors also have persistent menu, directions, and ordering actions. Hours link to the published restaurant schedule; no live open/closed claim is made without confirmed current hours. Menu and golf pages link to the published menus and course information while approved content is prepared for this site. Provider, Facebook, hours, menu, golf, and map destinations are configured in `georges_oasis/external_links.py`. The homepage retains its original exterior hero photograph and all content sections.

## Owner dashboard

Open `/admin` and sign in with username `username` and password `password` (demo credentials).

Use **Add an offer** to choose the weekly deals popup or coupons section, enter the title and terms, upload an optional image, and set start/end dates. Times use Allentown's Eastern timezone. Turn the offer on, then save. Blank dates mean immediate start/no expiration. The dashboard shows Hidden, Scheduled, Live, or Expired. Separate homepage switches can hide either feature without changing individual offers. The popup opens on each homepage load when active deals exist. No offers are seeded; add your approved content to see the features.

SQLite data, processed uploads, and the persistent session key are local in `instance/` (excluded from Git). Back up that directory together. Flask-Migrate revisions are in `migrations/`; run `flask --app app db upgrade` after pulling schema changes. For a new schema change, run `flask --app app db migrate -m "Describe change"` and review the revision before upgrading.

Run backend checks with `.venv/bin/python -m unittest discover -s tests`.
