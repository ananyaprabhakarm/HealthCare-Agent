# healthcare.agent

A conversational front door for booking doctor appointments. Patients and
doctors each get a chat assistant (backed by an LLM tool-calling loop) plus a
small dashboard — patients can see their appointments and browse doctors,
doctors can manage their weekly availability and see today's schedule.

**Live**: [health-care-agent-topaz.vercel.app](https://health-care-agent-topaz.vercel.app) (frontend) · backend on Render.

## Features

- **Landing page + auth** — email/password signup and login (JWT sessions), separate patient/doctor roles.
- **Patient dashboard**
  - Chat — check a doctor's availability or book a visit in plain language.
  - My Appointments — list of bookings with status (upcoming / in progress / done / cancelled), with a Cancel action.
  - Find a Doctor — directory with an "available today" badge and specialization filters; "Book" jumps into Chat with the request pre-filled.
- **Doctor dashboard**
  - Chat — ask about your schedule in plain language (e.g. "how many appointments today?").
  - Today's Schedule — a timeline of today's appointments.
  - Manage Availability — add/remove weekly availability slots (this is what patients can book against).
- **Backend**: FastAPI + SQLAlchemy, a small tool registry driving Gemini function-calling for the chat assistant, JWT auth, role-gated REST endpoints for the dashboard views.

## Tech stack

| | |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, SQLite (dev) / Postgres (prod), PyJWT, bcrypt |
| LLM | Google Gemini (`google-genai`) |
| Frontend | React, TypeScript, Vite, React Router |
| Deployment | Render (backend), Vercel (frontend) |

## Project structure

```
backend/
  app/
    auth.py            # password hashing, JWT issuance, get_current_user dependency
    models.py           # SQLAlchemy models
    schemas.py           # Pydantic request/response schemas
    db.py                # engine/session setup
    domain/
      appointments.py   # business logic: availability, booking, cancellation, stats
    agent/
      tools.py           # tool registry the LLM can call (one source of truth per tool)
      chat_service.py    # the chat/tool-calling loop shared by patient + doctor chat
      conversation.py    # rebuilds LLM conversation turns from stored chat history
    routes/
      auth.py, chat.py, doctor.py, doctors.py, patients.py
    services/
      llm.py, calendar.py, email.py, notification.py   # external integrations
    tests/
  main.py                # app entrypoint (loads .env, creates tables); run with uvicorn

frontend/
  src/
    pages/               # Landing, Login, Signup (+ marketing.css, dashboard.css)
    views/                # PatientAppointments, FindADoctor, DoctorSchedule, DoctorAvailability
    AppShell.tsx           # post-login sidebar + view switching
    AuthContext.tsx         # session state, login/signup/logout
    Chat.tsx                 # shared chat UI used by both roles
```

## Local setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Google Gemini API key](https://aistudio.google.com/apikey) (the app runs with a rule-based fallback parser if you skip this, but real conversation only works with a key)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # includes requirements.txt + pytest

cp .env.example .env
```

Edit `backend/.env`:
- `JWT_SECRET` — **required**, the app fails to start without it. Generate one with:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- `LLM_API_KEY` — your Gemini API key (optional but recommended).
- Everything else (Google Calendar, email, Slack/WhatsApp notifications) is optional — features that depend on them just no-op if left blank.

Run it:

```bash
uvicorn main:app --reload --port 8000
```

This creates `backend/dev.db` (SQLite) on first run and serves the API at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

Run the tests:

```bash
pytest app/tests
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

For local development against the backend above, leave `VITE_API_BASE_URL`
unset/empty in `frontend/.env` — Vite's dev server proxies `/api` to
`http://localhost:8000` automatically (see `vite.config.ts`). Only set
`VITE_API_BASE_URL` when pointing the frontend at a **deployed** backend.

```bash
npm run dev
```

Serves the app at `http://localhost:5173`.

Build for production:

```bash
npm run build   # runs tsc --noEmit && vite build
```

## Deployment

- **Backend (Render)**: config lives in `render.yaml`. Set these environment
  variables in the Render dashboard (they aren't in the yaml, since they're
  secrets): `JWT_SECRET`, `LLM_API_KEY`, and optionally `DATABASE_URL` (points
  at SQLite by default — use a real Postgres URL in production), plus any of
  the optional integration keys from `.env.example`.
- **Frontend (Vercel)**: set `VITE_API_BASE_URL` in the Vercel project's
  environment variables to your deployed backend's URL. This is a **build-time**
  variable — Vite bakes it into the bundle, so a plain `.env` file committed to
  the repo (it's gitignored anyway) won't reach Vercel's build; it must be set
  in Vercel's own dashboard.

## API overview

All endpoints are under `/api`. Full interactive schema at `/docs` on a running backend.

| | |
|---|---|
| `POST /api/auth/signup`, `/login`, `GET /me` | Auth |
| `POST /api/chat/patient`, `/api/chat/doctor` | Chat (LLM tool-calling loop) |
| `GET/POST /api/doctors/me/availability`, `DELETE .../{id}` | Doctor availability |
| `GET /api/doctors/me/schedule/today` | Doctor's today view |
| `GET /api/doctors` | Doctor directory (any authenticated user) |
| `POST /api/doctor/summary` | Doctor stats (used internally by the chat tool) |
| `GET /api/patients/me/appointments`, `PATCH .../{id}/cancel` | Patient appointments |

## Known gaps / not yet built

- No reschedule flow — cancel and rebook via chat instead.
- No cancellation email/calendar-invite notice (booking sends one on create; nothing symmetric fires on cancel).
- No doctor ratings, no medicine/prescriptions — out of scope for now, would need their own data model.
- No password reset, OAuth login, or email verification.
- No DB migration framework — schema changes currently need a manual `ALTER TABLE` against the deployed database.

## License

MIT — see [LICENSE](LICENSE).
