# Mark & Mind — Website (Static Site)

Full multi-page site implementing the earlier design plan: navy/gold justice
theme, background watermark line-art (scales, colonnade), gold hairline
dividers, pull-quote bands, and laurel emblem badges — all built as
self-contained SVGs, no stock imagery, so there are no licensing concerns.

## Pages

| File | Purpose |
|---|---|
| `index.html` | Homepage — hero, practice area cards, pull-quote, insights teaser, about teaser, contact CTA |
| `about.html` | Full bio, timeline, philosophy |
| `practice-areas.html` | All 4 practice areas in detail, process steps, FAQ |
| `insights.html` | Blog index with full content for the 3 existing posts |
| `contact.html` | Contact form, WhatsApp CTA, office info, map placeholder |
| `careers.html` | Job listings + application form — wired to the FastAPI Careers API built separately |
| `legal.html` | Disclaimer + Privacy Policy template |

Every page includes a BCI-compliant disclaimer gateway (shown once per visit,
on the homepage) and a floating WhatsApp button.

## Design system

All shared styles live in `assets/styles.css`. Key building blocks:

- **Watermarks**: `assets/scales-icon.svg` (used both in the header logo and
  as a low-opacity background watermark) and `assets/pillars.svg` (a
  repeating colonnade pattern, also low-opacity)
- **Emblem badges**: `assets/laurel.svg`, used around the credential stats
  (2024 / 3+ / 1:1) to make them read like a seal/certification mark
- **Pull-quote band**: `.quote-band` class — full-width navy band with a
  large serif quote, used on Home, About, Practice Areas, and Insights
- **Colors**: `--navy`, `--gold`, `--charcoal` defined once in `:root` in
  `styles.css` — change them there to retheme the whole site

## Connecting the Careers page to the API

`careers.html` expects the Careers API (in `mark-mind-service/`, see below)
to be reachable. Two ways to deploy:

1. **Serve this whole site as static files, API separately** — set
   `API_BASE` near the bottom of `careers.html` to your API's full URL,
   e.g. `const API_BASE = "https://api.markandmind.example.com";`
2. **Let the FastAPI app serve `/careers` itself** — `mark-mind-service`
   already does this by serving `app/static/careers.html`. In that case you'd
   only use this copy of `careers.html` as the source of truth and copy it
   (and any other edited pages/assets) into `mark-mind-service/app/static/`
   to keep them in sync.

## Contact form

`contact.html`'s form currently just shows a placeholder message on submit —
wire the `fetch()` call in its `<script>` tag to your backend
(`POST /api/contact` on `mark-mind-service`, see below), or to a service like
Formspree, to actually receive submissions.

## `mark-mind-service` — Careers & Contact API

A small FastAPI backend that powers the Careers job board/application flow
and the Contact form. It lives in `mark-mind-service/` and also serves the
static site itself (see `app/main.py`, which mounts `app/static/` at `/`).

**Storage**: file-backed YAML (see `app/storage.py`, data written under
`data/`) — no database is provisioned. There's dormant SQLAlchemy/Postgres
code (commented out in `app/database.py`, `app/models.py`, the routers, and
`docker-compose.yml`) that can be re-enabled later if the site outgrows YAML
storage.

### API routes

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | — | Health check |
| GET | `/careers` | — | Serves `careers.html` |
| GET | `/api/jobs` | — | List active job postings |
| GET | `/api/jobs/{slug}` | — | Get one active job |
| POST | `/api/jobs` | admin | Create a job posting |
| PATCH | `/api/jobs/{job_id}` | admin | Update a job posting |
| DELETE | `/api/jobs/{job_id}` | admin | Delete a job posting |
| POST | `/api/jobs/{slug}/apply` | — | Submit an application (form + resume upload) |
| GET | `/api/jobs/{slug}/applications` | admin | List applications for a job |
| PATCH | `/api/applications/{application_id}` | admin | Update an application's status |
| POST | `/api/contact` | — | Submit a contact form message |
| GET | `/api/contact` | admin | List contact messages |

Admin routes require an `X-API-Key` header matching `ADMIN_API_KEY` (see
`app/security.py`). Public submission routes (`apply`, `contact`) are
rate-limited per email address via `APPLY_RATE_LIMIT_COUNT` /
`APPLY_RATE_LIMIT_WINDOW_SECONDS`.

### Running locally

```bash
cd mark-mind-service
cp .env.example .env   # fill in ADMIN_API_KEY, etc.
docker compose up --build
```

The API (and static site) will be available at `http://localhost:8000`.
Uploaded resumes and YAML data persist in the `resumes`/`data` Docker
volumes.

Without Docker:

```bash
cd mark-mind-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Key environment variables (`.env.example`)

| Variable | Purpose |
|---|---|
| `ADMIN_API_KEY` | Secret required in `X-API-Key` for admin routes |
| `MAX_UPLOAD_MB` | Max resume upload size |
| `APPLY_RATE_LIMIT_COUNT` / `APPLY_RATE_LIMIT_WINDOW_SECONDS` | Rate limiting for applications/contact messages |

### Deploying (Render)

`render.yaml` defines a single Docker web service with a persistent disk
mounted at `/app/data` (required since Render's filesystem is otherwise
ephemeral — disks need a paid plan, not the free tier). `ADMIN_API_KEY` is
auto-generated by Render; other env vars mirror `.env.example`.

**Note**: email notifications (to the practice's inbox) on new applications/
contact messages are not yet wired up — see the `# In production:` comments
in `app/routers/applications.py` and `app/routers/contact.py`.

## Before publishing

- Replace the photo placeholder in `about.html` with a real headshot
- Replace phone/email placeholders if they change
- Have `legal.html` reviewed against current BCI advertising rules — the
  disclaimer text here follows common practice among Indian advocate sites
  but isn't a substitute for review by qualified counsel on compliance specifically
- Add the Google Maps embed in `contact.html` where marked
