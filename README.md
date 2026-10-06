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

The supplied design is served at `/`. The following routes currently render shared placeholder pages while their content is developed:

`/menu`, `/ice-cream`, `/mini-golf`, `/parties`, `/specials`, `/visit`, `/about`, and `/order`.

## Owner dashboard

Open `/admin` and sign in with username `username` and password `password` (demo credentials).

Use **Add an offer** to choose the weekly deals popup or coupons section, enter the title and terms, upload an optional image, and set start/end dates. Times use Allentown's Eastern timezone. Turn the offer on, then save. Blank dates mean immediate start/no expiration. The dashboard shows Hidden, Scheduled, Live, or Expired. Separate homepage switches can hide either feature without changing individual offers. The popup opens on each homepage load when active deals exist. No offers are seeded; add your approved content to see the features.

SQLite data, processed uploads, and the persistent session key are local in `instance/` (excluded from Git). Back up that directory together. Flask-Migrate revisions are in `migrations/`; run `flask --app app db upgrade` after pulling schema changes. For a new schema change, run `flask --app app db migrate -m "Describe change"` and review the revision before upgrading.

Run backend checks with `.venv/bin/python -m unittest discover -s tests`.
