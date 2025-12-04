## Doctor appointment and reporting assistant (MCP-style)

This repo implements a minimal full-stack prototype of an agentic doctor assistant:

- **Backend**: FastAPI with database models and MCP-style tool layer
- **Database**: PostgreSQL (via SQLAlchemy, with a SQLite default for local dev)
- **Frontend**: React (Vite) chat UI for patients and doctors
- **LLM integration**: Pluggable client layer where an MCP-aware LLM can orchestrate tools

The goal is to support:

- Natural-language appointment scheduling from patients
- Multi-turn interactions with context
- Doctor-facing summaries of recent and upcoming appointments
- A secondary notification channel for doctor reports

### Structure

- `backend/`
  - `main.py`: FastAPI entrypoint
  - `app/db.py`: SQLAlchemy engine and session
  - `app/models.py`: core tables (doctors, patients, availability, appointments, chat sessions)
  - `app/schemas.py`: Pydantic request/response models
  - `app/routes/`: HTTP endpoints
  - `app/services/`: calendar, email, notification, LLM integration stubs
  - `app/mcp/tools.py`: core tool implementations the LLM can call
- `frontend/`
  - Vite + React SPA with a patient chat view and doctor dashboard

### Running the backend

From the repo root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg2://USER:PASSWORD@localhost:5432/doctor_assistant"  # or omit to use SQLite
uvicorn main:app --reload
```

This exposes the FastAPI app at `http://localhost:8000` with:

- `POST /api/chat/patient`
- `POST /api/chat/doctor`
- `POST /api/doctor/summary`

The first import of `backend/main.py` creates the tables automatically.

### Running the frontend

From the repo root:

```bash
cd frontend
npm install
npm run dev
```

Vite serves the UI on `http://localhost:5173` and proxies `/api` to the backend.

### Seeding data for testing

At minimum you need:

- A `Doctor` row for the target doctor (for example, Dr. Ahuja).
- Matching `DoctorAvailability` rows for the weekdays you want to test.

You can insert these via SQLAlchemy shell, Alembic seed, or manual SQL.

### How the flows work

- Patients use the patient chat view to ask for availability and bookings.
- Doctors use the doctor chat or the summary buttons for quick statistics.
- The backend exposes MCP-style tools (`get_doctor_availability`, `create_appointment`, `get_appointment_stats`, `send_doctor_notification`) in `app/mcp/tools.py`.
- A real deployment would plug an actual MCP client + LLM into `app/services/llm.py` and dispatch real Google Calendar, email, and notification calls by enabling those clients in `app/services`.
