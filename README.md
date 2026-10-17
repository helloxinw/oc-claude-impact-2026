# ReferralFlow — React + Tailwind + shadcn/ui + FastAPI + PostgreSQL + Alembic

A hackathon starter for *synthetic* recuperative-care intake. Frontend is React + TypeScript + Vite + Tailwind CSS v4, with **locally owned shadcn/ui-style components** (Radix UI dialog/select and reusable UI files in `frontend/src/components/ui/`). API is FastAPI + SQLAlchemy; persistence is PostgreSQL; migrations are handled by Alembic. No Claude integration, document uploads, login, or real-patient data safeguards yet.

## Requirements

- Docker Desktop with Docker Compose
- Python 3.11+
- Node.js **22.12+** (or the current minimum supported by Vite) and npm

## 1. Database (terminal 1)

```bash
docker compose up -d db
```

Postgres listens at `127.0.0.1:5433` (chosen to avoid a local Postgres conflict). Dev-only credentials are in `compose.yaml` and `backend/.env.example`.

## 2. Backend and migrations (terminal 2)

```bash
cd backend
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`alembic upgrade head` is **required on a fresh DB**. FastAPI no longer calls `Base.metadata.create_all`; versioned migrations manage the schema. The API seeds 3 fictional referrals when the table is empty (set `DEMO_SEED=false` to opt out).

Try http://127.0.0.1:8000/docs and http://127.0.0.1:8000/api/health.

If you previously ran the old starter against this *same* DB, it may already contain the `referrals` table without Alembic's `alembic_version` table. Inspect its schema first and, **only if it exactly matches the initial migration**, run `alembic stamp 0001` instead of running `alembic upgrade head`. Never blindly stamp an unknown schema. Alternatively use a brand-new Docker volume for this fresh hackathon project; **`docker compose down -v` irreversibly deletes your local demo database**.

## 3. Frontend (terminal 3)

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. Vite proxies `/api` calls to `127.0.0.1:8000`.

Create a fictional referral, refresh the browser to verify persistence, click a referral, filter/search cases, and update its status. Data is stored in PostgreSQL.

## Database development workflow

Change SQLAlchemy models under `backend/app/models.py`, then, while Postgres is running and the backend virtualenv is activated:

```bash
cd backend
alembic revision --autogenerate -m "add referral documents"
# Review the generated migration's upgrade() / downgrade() operations carefully
alembic upgrade head
alembic current
```

Autogenerate does **not** reliably detect every rename or data migration. Check scripts before running. `alembic downgrade -1` is possible but can remove data when reverting destructive migrations. Migrations should be committed with code.

## UI changes

- Tailwind CSS v4 is configured through `frontend/src/index.css` and the Vite plugin.
- Import alias `@/` points to `frontend/src/`.
- `frontend/components.json` configures the official shadcn CLI for adding further components.
- Existing UI primitives live in `frontend/src/components/ui/`: `button`, `badge`, `card`, `table`, `input`, `textarea`, `label`, `dialog`, `select`. They follow the shadcn copy-into-repo approach and can be edited directly.

To install more components:

```bash
cd frontend
npx shadcn@latest add tabs skeleton separator
```

If the CLI asks before overwriting one of the starter UI components, **keep your local file** unless you intend to replace it.

## REST endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | API and database health |
| GET | `/api/referrals` | Queue |
| POST | `/api/referrals` | Create synthetic referral |
| GET | `/api/referrals/{id}` | Case details |
| PATCH | `/api/referrals/{id}` | Manually update status |

## Next hackathon feature

1. Migration: `documents` table (referral ID, filename, file path, upload timestamp).
2. Migration: `findings` table (key, value, source-document ID/page, needs-verification status).
3. `POST /api/referrals/{id}/documents` for synthetic PDF upload (validate type, size, and storage path).
4. FastAPI server-side Claude API call for structured extraction and source citations; persist the result.
5. Reviewer UI showing checklist, supporting evidence, and drafts requesting missing information.

**Security scope:** this is a local demonstration using fictional patients only. No PHI, real hospital documents, or real patient identifiers. For actual healthcare deployment, obtain organizational approval and implement legal/contractual, privacy, security, authentication, auditing and retention controls.
