# ReferralFlow — Project Instructions

## Overview

ReferralFlow is a hackathon prototype that helps recuperative-care coordinators review hospital referral packets, identify missing information, and track referral statuses. The goal is to reduce manual review and communication overhead.

## Tech Stack

- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, shadcn/ui (Radix UI primitives).
- **Backend:** Python, FastAPI, SQLAlchemy, Pydantic. REST API architecture.
- **Database:** PostgreSQL via Docker Compose, with Alembic for schema migrations.
- **AI:** Claude API (planned) for PDF extraction and referral analysis.

## Repository Structure

```text
/
├── frontend/
│   ├── src/
│   │   ├── components/ui/  # shadcn UI components
│   │   ├── App.tsx         # Main application
│   │   ├── api.ts          # REST API client
│   │   ├── types.ts        # TypeScript interfaces
│   │   └── index.css       # Tailwind styles
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI entry point
│   │   ├── database.py     # SQLAlchemy connection
│   │   ├── models.py       # Database models
│   │   ├── schemas.py      # Pydantic schemas
│   │   └── routers/        # REST API routes
│   ├── alembic/            # Database migrations
│   └── requirements.txt
└── compose.yaml            # PostgreSQL container
```

## Development Guidelines

- Follow existing project conventions and keep implementations simple.
- Use functional React components, TypeScript, Tailwind, and shadcn/ui.
- Keep frontend API calls centralized in `api.ts`.
- Use FastAPI routers, Pydantic schemas, and SQLAlchemy models.
- Manage database schema changes through Alembic, not `create_all()`.
- Keep AI processing and business logic separate from API routes.
- Never expose API keys in frontend code.
- Use synthetic patient data only. This prototype is not approved for real patient information.
- Prioritize working end-to-end functionality over unnecessary abstractions.

## Local Development

- Database: `docker compose up -d db`
- Backend: `cd backend && alembic upgrade head && uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm run dev`
- API docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`
