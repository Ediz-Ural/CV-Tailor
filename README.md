# CV-Tailor

CV-Tailor is a multi-user web application that reads a job posting, picks the most relevant experience, projects and skills from your profile pool, and produces a CV tailored to that posting. The pool is fed from PDFs, GitHub and manual entries; the selected material is rephrased for the posting **without inventing anything** and rendered to PDF with Typst.

## Screens

| Profile pool | Posting → CV |
|---|---|
| ![Profile pool](docs/screenshots/02-pool.png) | ![Pipeline running](docs/screenshots/03-pipeline-running.png) |

When the pipeline finishes, the ATS score, the before/after diff, the selected pool items and the PDF preview all open on the same screen:

![CV result](docs/screenshots/04-result.png)

| CV archive | Account and API key |
|---|---|
| ![Archive](docs/screenshots/05-archive.png) | ![Account](docs/screenshots/06-account.png) |

## How it works

There are two LangGraph flows:

**Pool flow** — The PDF of the CV you upload and the GitHub repository you connect are parsed, candidates are extracted, and they are presented **for your approval**. Nothing you have not approved is ever used in CV generation.

**Generation flow** — `JobParser` turns the posting into structured requirements → `Selector` pulls candidates from the pool by pgvector similarity and picks the ones that fit the posting → `CVTailor` rephrases the selection for the posting → `Evaluator` produces the ATS match score, the missing keywords and the before/after diff → `TypstRenderer` renders the PDF. The interface follows the steps live.

### How selection behaves

Your pool can hold projects from any field; only the ones matching the posting make it onto the CV. Measured with a 15-project pool spread across five fields:

| Posting | Projects on the CV |
|---|---|
| AI Engineer | 2 AI projects |
| Frontend Engineer | 3 frontend projects |
| DevOps / SRE | 3 infrastructure projects |
| Mobile Engineer | 3 mobile projects |

In none of the four postings did a project from another field make it onto the CV. The selection limit is a ceiling, not a quota: if three projects match the posting, the CV carries three projects.

This behaviour is governed by three settings — `SELECTOR_CANDIDATE_LIMIT` (how many candidates the vector search hands to the ranker; raise it for a large portfolio), `SELECTOR_SELECTION_LIMIT` (the most projects a CV may carry) and `SELECTOR_MIN_RELEVANCE` (how relevant a project must be to be included at all; lower it to let borderline work in, raise it to keep the CV tighter).

## Highlights

- **Your own API key.** Generation is billed to your own provider account; the key is stored encrypted and is never returned in any response.
- **No fabrication.** The model only rephrases pool items you have approved.
- **TR/EN interface** and multi-tenant data isolation.
- **KVKK** (the Turkish data protection law): explicit consent flow, disclosure text and one-click permanent account deletion.

## Tech stack

FastAPI · LangGraph · PostgreSQL + pgvector · SQLAlchemy + Alembic · Typst · React 19 + Vite + Tailwind · Docker Compose · pytest · Vitest · Playwright

## Setup

### One command

On Windows all you need is Docker Desktop running and [Node.js](https://nodejs.org/) installed. The script handles the rest:

```powershell
.\dev.ps1
```

This happens in order: if there is no `.env` it is generated from `.env.example` with a random `JWT_SECRET` and random encryption keys → PostgreSQL is brought up in Docker → `uv` and Typst are downloaded if missing → dependencies are installed → migrations run → the backend on `:8000` and the interface on `:5173` open in separate windows → once both answer healthy, the browser opens.

```
[1/6] .env hazirlaniyor... olusturuldu
[2/6] PostgreSQL (docker) baslatiliyor... hazir
[3/6] Backend bagimliliklari (uv sync)... tamam
[4/6] Migration'lar (alembic upgrade head)... tamam
[5/6] Backend :8000 ... ok
[6/6] Frontend :5173 ... ok
```

On the screen that opens, create an account with **Kayıt ol** (Sign up); nothing else is needed to log in. When you want to generate a CV, you enter your own LLM API key on the **Hesap** (Account) screen — generation is billed to your own provider account.

| Flag | What it does |
|---|---|
| `.\dev.ps1` | Installs and starts |
| `.\dev.ps1 -SkipInstall` | Skips the `uv sync` / `npm install` steps for a faster restart |
| `.\dev.ps1 -NoBrowser` | Does not open the browser |
| `.\dev.ps1 -Stop` | Stops the backend, the interface and the database |

Four things the script quietly takes care of:

- **Your `.env` is not overwritten.** Only fields still holding the example value or left empty are filled in; nothing you entered yourself is touched.
- **The database address.** `DATABASE_URL` in `.env` points at the `db` host for Compose. A backend running locally reaches the same database over `localhost`; that value is not written to the file, it is only passed to the started process as an environment variable.
- **Typst.** If it is not on PATH, the Windows build is downloaded into `.tools/` and `TYPST_BINARY` is pointed there — otherwise the pipeline fails at the `typst_renderer` step.
- **A `.venv` leaking out of Docker.** A `backend/.venv` produced inside Docker does not work on Windows and `uv sync` cannot remove it; the script recognises such an environment and cleans it up.

Two things to expect on the first run:

- **The first install takes a few minutes** (Python dependencies, `npm install`, the Typst download).
- **The first item added to the pool takes about 1.5 minutes.** `EMBEDDING_MODEL` is downloaded on first use (about 2 GB); later requests return immediately. The screen may look frozen — waiting is enough.

### Manual setup

If you are not using the script (or you are not on Windows), prepare the environment file first:

```powershell
Copy-Item .env.example .env
```

Make sure to change `JWT_SECRET` — the value in `.env.example` is public, and anyone who knows it can mint a token for any account:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Generate a Fernet key for `CREDENTIAL_ENCRYPTION_KEY` (it encrypts users' GitHub tokens and LLM keys):

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### Path 1 — The whole stack in Docker

```powershell
docker compose --env-file .env -f infra/docker-compose.yml --profile app up --build
```

`--env-file .env` is required: Compose looks for the `.env` file relative to the directory holding the compose file (`infra/`), so without this flag the `.env` in the repository root is silently ignored and `LLM_API_KEY` stays empty.

The interface opens on `http://localhost:8080` and the API on `http://localhost:8000`. The interface proxies the `/api` path to the backend through its own nginx. The first build takes a few minutes: the backend image downloads Typst and the frontend image runs `npm ci`.

CV generation needs an LLM provider key, **but that key does not go into `.env`**: every user enters their own key on the **Hesap** (Account) screen in the app, and generation is billed to that user's own provider account. The key is validated against the provider when it is saved, stored encrypted, and never shown again.

On a single-person install you can share the server's `LLM_API_KEY` by setting `ALLOW_SHARED_LLM_KEY=1`; do not turn this on for an install with more than one account, because every user then spends your key.

#### Path 2 — Database in Docker, application locally

This is the flow `.\dev.ps1` automates; by hand it goes like this:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d db

cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# in a second terminal
cd frontend
npm install
npm run dev
```

The interface opens on `http://localhost:5173` and Vite's proxy forwards `/api` requests to `http://localhost:8000`.

Things to know:

- **Point `DATABASE_URL` at localhost.** The value in `.env` refers to the `db` host inside the Compose network; for a locally running backend it must be `localhost`.
- **The virtual environment is not shareable.** `backend/.venv` is not under version control, and a venv produced inside Docker does not work on Windows. Always create your own environment locally with `uv sync`.
- **PDF rendering needs the Typst binary.** If you run the backend outside Docker, [Typst](https://github.com/typst/typst) must be installed and `TYPST_BINARY` must point at it; otherwise the pipeline fails at the `typst_renderer` step. The Docker image installs Typst itself.
- **`RENDER_OUTPUT_DIR` and `FASTEMBED_CACHE_PATH`** point at in-container paths (`/app/storage/...`, `/var/cache/fastembed`) in `.env`; change them to existing directories when running locally.
- **Calls from the browser need an allowed origin.** If you will call the API directly rather than through the `/api` proxy, add the origin to the `CORS_ALLOW_ORIGINS` list.
- **The GitHub OAuth return.** `GITHUB_OAUTH_REDIRECT_URI` is the backend's callback address, while `FRONTEND_BASE_URL` is the interface address the user is sent back to.

## Tests

```powershell
# backend (against a real PostgreSQL)
cd backend
uv run pytest

# frontend unit tests
cd frontend
npm test

# end-to-end (requires a running backend)
cd frontend
npx playwright install chromium
npm run test:e2e
```

The end-to-end tests drive the production build against a real API and database; none of them reach an LLM provider, so no paid key is required.

The backend tests connect to a real PostgreSQL and delete the rows in its tables. For that reason they only run against a database whose name ends in `_test` or `_ci`:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml exec db createdb -U cv_tailor cv_tailor_test
$env:DATABASE_URL = "postgresql+psycopg://cv_tailor:cv_tailor_dev@localhost:5432/cv_tailor_test"
cd backend
uv run alembic upgrade head
uv run pytest
```

If you knowingly accept your development database being wiped, you can disable this check with `CV_TAILOR_ALLOW_DESTRUCTIVE_TESTS=1`.

## Production deployment

1. Copy `.env.example` to `.env` and replace at least these values with real production ones: `POSTGRES_PASSWORD`, `DATABASE_URL`, `JWT_SECRET`, `CREDENTIAL_ENCRYPTION_KEY`, `GITHUB_OAUTH_CLIENT_SECRET`, `FRONTEND_BASE_URL`. `LLM_API_KEY` is not needed; users enter their own keys.
   Since the interface reaches the API through its own nginx, `CORS_ALLOW_ORIGINS` can be left empty; if you will call the API from another origin, put that address here.
2. Build the production images and start the stack:

```powershell
docker compose --env-file .env -f infra/docker-compose.prod.yml up -d --build
```

3. Check health and metrics:

```powershell
Invoke-RestMethod http://localhost:8080/api/health
Invoke-RestMethod http://localhost:8080/api/metrics
```

4. Watch the backend JSON logs:

```powershell
docker compose --env-file .env -f infra/docker-compose.prod.yml logs -f backend
```

The logs carry `request_completed`, `pipeline_step_started`, `pipeline_step_completed`, `pipeline_completed` and `pipeline_failed` events as JSON. Every step in the pipeline status response carries a `duration_ms` field; `/metrics` returns the pipeline status counts and the render queue counters.

## Smoke flow

With the production stack up:

1. Create a user with `POST /api/auth/register`.
2. Get a token with `POST /api/auth/login`.
3. Add a manual, verified pool item with the token.
4. Send a posting text with `POST /api/cv-generation`.
5. Call `GET /api/cv-generation/{pipeline_id}` for the returned `pipeline_id`.
6. Verify `status=completed`, `generated_cv_id`, `ats_score` and the per-step `duration_ms` fields.
7. Fetch the PDF with `GET /api/generated-cvs/{generated_cv_id}/download`.

## Repository layout

```
dev.ps1     Script that sets up and starts the whole development environment with one command
backend/    FastAPI application, LangGraph flows, Alembic migrations, pytest
frontend/   React + Vite interface, Vitest unit tests, Playwright e2e
infra/      Docker Compose (development and production) and database bootstrap scripts
docs/       Data retention and security policy, work package documents
```

## Contributing and license

Issues and pull requests are welcome. Before sending a change, make sure `npm run lint`, `npm test` and `uv run pytest` pass; CI runs the same three plus the end-to-end tests.

Licensed under MIT, see [LICENSE](LICENSE).
